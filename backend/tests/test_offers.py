import pytest

from .helpers import client, login, post_listing, post_requirement, register, reset_db


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    reset_db()
    yield


def _setup(phone_f, phone_b, qty=100):
    farmer, buyer = register("farmer", phone_f, lang="te"), register("buyer", phone_b)
    rid = post_requirement(buyer)
    lid = post_listing(farmer, qty=qty)
    return farmer, buyer, lid, rid


def test_negotiation_payment_rating_and_outcome():
    farmer, buyer, lid, rid = _setup("6000000001", "6000000002")
    client.get(f"/recommendations/{lid}", headers=farmer)   # stores opportunities (for decision feedback)

    r = client.post("/offers", headers=buyer, json={"listing_id": lid, "requirement_id": rid, "price": 2400, "quantity": 80})
    assert r.status_code == 201, r.text
    oid = r.json()["id"]
    assert r.json()["can_respond"] is False
    # duplicate active offer blocked
    assert client.post("/offers", headers=buyer, json={"listing_id": lid, "price": 2410, "quantity": 80}).status_code == 409
    # buyer cannot answer own offer; farmer counters
    assert client.post(f"/offers/{oid}/respond", headers=buyer, json={"action": "accept"}).status_code == 409
    r = client.post(f"/offers/{oid}/respond", headers=farmer, json={"action": "counter", "price": 2480})
    assert r.status_code == 200 and r.json()["price"] == 2480 and r.json()["last_actor"] == "farmer"
    assert client.post(f"/offers/{oid}/respond", headers=buyer, json={"action": "accept"}).json()["status"] == "accepted"
    # payment flow
    assert client.post(f"/offers/{oid}/confirm-payment", headers=farmer).status_code == 409   # nothing paid yet
    r = client.post(f"/offers/{oid}/payment", headers=buyer, json={"method": "upi", "reference": "UPI123"})
    assert r.json()["payment_status"] == "paid" and r.json()["payment_amount"] == 2480 * 80
    assert client.post(f"/offers/{oid}/payment", headers=farmer, json={"method": "upi"}).status_code == 409
    r = client.post(f"/offers/{oid}/confirm-payment", headers=farmer)
    assert r.json()["status"] == "completed"
    # ratings (Bayesian average moves reliability)
    r = client.post(f"/offers/{oid}/rate", headers=farmer, json={"score": 5})
    assert r.status_code == 200 and r.json()["reliability"] == pytest.approx((4.0 * 3 + 5) / 4)
    assert client.post(f"/offers/{oid}/rate", headers=farmer, json={"score": 1}).status_code == 409
    # decision feedback recorded
    admin = login("9999999999", "admin123")
    ov = client.get("/admin/overview", headers=admin).json()
    assert ov["offers"]["completed"] == 1 and ov["decision_feedback"]["deals"] == 1
    # Telugu notifications for the farmer
    notes = client.get("/notifications", headers=farmer).json()
    assert any("ఆఫర్" in n["title"] for n in notes)
    # listing is sold -> no more offers
    assert client.post("/offers", headers=buyer, json={"listing_id": lid, "price": 2400, "quantity": 10}).status_code == 404


def test_reject_cancel_and_quantity_limits():
    farmer, buyer, lid, rid = _setup("6000000011", "6000000012")
    assert client.post("/offers", headers=buyer, json={"listing_id": lid, "price": 2400, "quantity": 500}).status_code == 400
    oid = client.post("/offers", headers=buyer, json={"listing_id": lid, "price": 2400, "quantity": 50}).json()["id"]
    assert client.post(f"/offers/{oid}/respond", headers=farmer, json={"action": "reject"}).json()["status"] == "rejected"
    # a farmer may start an offer toward a buyer requirement
    r = client.post("/offers", headers=farmer, json={"listing_id": lid, "requirement_id": rid, "price": 2450, "quantity": 60})
    assert r.status_code == 201
    oid = r.json()["id"]
    assert client.post(f"/offers/{oid}/cancel", headers=farmer).json()["status"] == "cancelled"


def test_dispute_and_admin_resolution():
    farmer, buyer, lid, rid = _setup("6000000021", "6000000022")
    oid = client.post("/offers", headers=buyer, json={"listing_id": lid, "price": 2400, "quantity": 50}).json()["id"]
    client.post(f"/offers/{oid}/respond", headers=farmer, json={"action": "accept"})
    r = client.post(f"/offers/{oid}/dispute", headers=buyer, json={"reason": "Quality does not match grade"})
    assert r.json()["status"] == "disputed"
    admin = login("9999999999", "admin123")
    assert any(d["offer_id"] == oid for d in client.get("/admin/disputes", headers=admin).json())
    assert client.post(f"/admin/disputes/{oid}/resolve?outcome=cancel", headers=admin).json()["status"] == "cancelled"
    # listing reopened
    assert client.get("/farmer/listings", headers=farmer).json()[0]["status"] == "open"


def test_groups_pooling_gain():
    reset_db()
    f1, f2 = register("farmer", "6100000001"), register("farmer", "6100000002", lat=16.75, lon=81.1)
    buyer = register("buyer", "6100000003")
    post_requirement(buyer, qty=400, price=2500, quality="C")
    l1, l2 = post_listing(f1, qty=150), post_listing(f2, qty=150)
    g = client.post("/groups", headers=f1, json={"name": "Eluru paddy", "crop": "paddy", "listing_id": l1})
    assert g.status_code == 201
    gid = g.json()["id"]
    assert client.get(f"/groups/{gid}/recommendations", headers=f2).status_code == 403   # must join first
    assert client.post(f"/groups/{gid}/join", headers=f2, json={"listing_id": l2}).status_code == 200
    assert client.post(f"/groups/{gid}/join", headers=f2, json={"listing_id": l2}).status_code == 409
    r = client.get(f"/groups/{gid}/recommendations", headers=f2).json()
    assert r["group"]["total_quintals"] == 300 and r["recommendations"]
    assert "pooling_gain" in r and len(r["member_shares"]) == 2
    assert sum(s["pooled_share"] for s in r["member_shares"]) == pytest.approx(r["pooled_net"], abs=0.05)
