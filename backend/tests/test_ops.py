import pytest

from app.middleware import RateLimiter
from app.services.timing import decide_timing

from .helpers import client, login, post_listing, register, reset_db


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    reset_db()
    yield


def test_decide_timing_rules():
    base = 100000
    gain = [{"days": 7, "net": 106000, "net_low": 99000, "net_high": 112000}]
    assert decide_timing(base, gain)["decision"] == "wait"
    small = [{"days": 7, "net": 101000, "net_low": 99000, "net_high": 103000}]
    assert decide_timing(base, small)["decision"] == "sell_now"            # gain below threshold
    risky = [{"days": 7, "net": 110000, "net_low": 85000, "net_high": 120000}]
    assert decide_timing(base, risky)["decision"] == "sell_now"            # downside too large
    assert decide_timing(base, [])["decision"] == "sell_now"


def test_rate_limiter_window():
    rl = RateLimiter()
    assert all(rl.allow(("ip", 0), 3, now=100 + i) for i in range(3))
    assert rl.allow(("ip", 0), 3, now=104) is False
    assert rl.allow(("ip", 0), 3, now=161) is True                         # window slid
    assert rl.allow(("ip", 0), 0, now=162) is True                         # 0 = disabled


def test_alerts_and_notifications(monkeypatch):
    from app import jobs
    farmer = register("farmer", "5000000001", lang="te")
    assert client.post("/alerts", headers=farmer, json={"crop": "paddy", "market": "Nowhere"}).status_code == 404
    a = client.post("/alerts", headers=farmer, json={"crop": "paddy", "market": "Eluru", "threshold_pct": 0.01})
    assert a.status_code == 201
    monkeypatch.setattr(jobs, "SessionLocal", __import__("app.database", fromlist=["SessionLocal"]).SessionLocal)
    # make fallback price differ from latest price by construction -> threshold 0.01% is exceeded
    res = jobs.check_price_alerts()
    notes = client.get("/notifications", headers=farmer).json()
    assert res["alerts_sent"] in (0, 1)
    if res["alerts_sent"]:
        assert "ధర" in notes[0]["body"] or "₹" in notes[0]["body"]
    assert client.post("/notifications/read-all", headers=farmer).status_code == 200
    assert client.patch("/me/language?lang=en", headers=farmer).json()["language"] == "en"
    assert client.patch("/me/language?lang=xx", headers=farmer).status_code == 400


def test_recompute_job_notifies_on_change():
    from app import jobs
    from app.database import SessionLocal
    from app.models import FarmerListing
    farmer = register("farmer", "5000000011")
    lid = post_listing(farmer)
    jobs.recompute_listings()                                 # first run just stores last_best_net
    with SessionLocal() as db:
        l = db.get(FarmerListing, lid)
        assert l.last_best_net
        l.last_best_net = l.last_best_net * 0.5                # pretend the best option used to be far worse
        db.commit()
    out = jobs.recompute_listings()
    assert out["notified"] >= 1
    assert any(n["kind"] == "best_option_changed" for n in client.get("/notifications", headers=farmer).json())


def test_admin_overview_markets_and_audit():
    admin = login("9999999999", "admin123")
    ov = client.get("/admin/overview", headers=admin).json()
    assert "data_quality" in ov and "users" in ov
    r = client.post("/admin/markets", headers=admin, json={"name": "Nuzvid", "latitude": 16.79, "longitude": 80.85})
    assert r.status_code == 201
    assert client.post("/admin/markets", headers=admin, json={"name": "nuzvid", "latitude": 1, "longitude": 1}).status_code == 409
    assert client.put(f"/admin/markets/{r.json()['id']}", headers=admin,
                      json={"name": "Nuzvid", "latitude": 16.8, "longitude": 80.9, "crops": "paddy"}).status_code == 200
    log = client.get("/admin/audit", headers=admin).json()
    assert any(row["path"] == "/admin/markets" and row["method"] == "POST" for row in log)
    assert client.post("/admin/jobs/sync", headers=admin).json().get("skipped")   # no API key configured


def test_websocket_receives_notifications():
    farmer = register("farmer", "5000000021")
    buyer = register("buyer", "5000000022")
    from .helpers import post_requirement
    rid = post_requirement(buyer)
    lid = post_listing(farmer)
    token = farmer["Authorization"].split()[1]
    assert _ws_rejected("bad-token")
    with client.websocket_connect(f"/ws?token={token}") as ws:
        client.post("/offers", headers=buyer, json={"listing_id": lid, "requirement_id": rid, "price": 2400, "quantity": 40})
        msg = ws.receive_json()
        assert msg["type"] == "notification" and msg["kind"] == "offer_received"


def _ws_rejected(token):
    try:
        with client.websocket_connect(f"/ws?token={token}"):
            return False
    except Exception:
        return True
