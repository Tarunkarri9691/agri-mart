"""End-to-end test of the FIG. 2 flow through the HTTP API."""
import pytest

from .helpers import client, post_listing, post_requirement, register, reset_db


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    reset_db()
    yield


def test_full_flow_with_ranges_msp_and_explain():
    farmer, buyer = register("farmer", "7000000001"), register("buyer", "7000000002")
    post_requirement(buyer)
    lid = post_listing(farmer)
    r = client.get(f"/recommendations/{lid}", headers=farmer)
    assert r.status_code == 200
    recs = r.json()
    assert len(recs) == 3 and [x["rank"] for x in recs] == [1, 2, 3]
    assert recs[0]["score"] >= recs[1]["score"] >= recs[2]["score"]
    assert {"buyer", "market"} == {x["candidate_type"] for x in recs}
    for x in recs:
        assert x["risk_tag"] in ("low", "moderate", "high")
        assert x["net_low"] <= x["net_realization"] * 1.001 and x["net_high"] >= x["net_realization"] * 0.999
        assert x["trips"] == 1 and x["msp"] == 2369
    mandi = next(x for x in recs if x["candidate_type"] == "market")
    assert mandi["below_msp"] is True            # synthetic mandi prices ~2200-2350 < MSP 2369
    assert mandi["net_low"] < mandi["net_high"]  # forecast interval -> net range
    e = client.get(f"/recommendations/{lid}/explain?rank=1", headers=farmer).json()
    assert {"price_factors", "cost_factors", "risk_factors", "ranking"} <= e.keys()


def test_timing_endpoint():
    farmer = register("farmer", "7000000011")
    lid = post_listing(farmer)
    t = client.get(f"/recommendations/{lid}/timing", headers=farmer)
    assert t.status_code == 200
    body = t.json()
    assert body["decision"] in ("sell_now", "wait") and "options" in body and "sell_now" in body


def test_large_lot_needs_multiple_trucks():
    farmer = register("farmer", "7000000012")
    lid = post_listing(farmer, qty=250)
    recs = client.get(f"/recommendations/{lid}", headers=farmer).json()
    assert recs and all(r["trips"] == 3 for r in recs if r["candidate_type"] == "market")


def test_role_and_auth_enforced():
    assert client.get("/farmer/listings").status_code == 401
    buyer = register("buyer", "7000000003")
    assert client.get("/farmer/listings", headers=buyer).status_code == 403
    assert client.post("/admin/retrain", headers=buyer).status_code == 403
    assert client.get("/admin/overview", headers=buyer).status_code == 403


def test_duplicate_phone_rejected():
    r = client.post("/auth/register", json={"name": "x", "phone": "7000000001", "password": "secret1", "role": "farmer",
                                            "latitude": 1, "longitude": 1})
    assert r.status_code == 409


def test_price_predict_endpoint_and_msp():
    r = client.get("/prices/predict", params={"crop": "paddy", "market": "Eluru"})
    assert r.status_code == 200
    j = r.json()
    assert j["low"] < j["predicted_price"] < j["high"]
    assert client.get("/msp").json()["paddy"] == 2369


def test_buyers_outside_radius_are_ignored():
    farmer, buyer = register("farmer", "7000000021"), register("buyer", "7000000022", lat=28.6, lon=77.2, name="DelhiBuyer")  # Delhi
    post_requirement(buyer, lat=28.6, lon=77.2)
    lid = post_listing(farmer)
    names = [r["name"] for r in client.get(f"/recommendations/{lid}", headers=farmer).json()]
    assert names and "DelhiBuyer" not in names
