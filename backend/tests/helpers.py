from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Market, MarketPrice, User
from app.security import hash_password

client = TestClient(app)


def reset_db(markets=(("Eluru", 16.7107, 81.0952, 2200), ("Vijayawada", 16.5062, 80.6480, 2350)), days=60, crop="paddy", crops="paddy"):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    for name, lat, lon, base in markets:
        m = Market(name=name, district=name, latitude=lat, longitude=lon, crops=crops)
        db.add(m)
        db.flush()
        for i in range(days):
            p = base + (i % 7) * 5
            db.add(MarketPrice(market_id=m.id, crop=crop, date=date.today() - timedelta(days=days - 1 - i), min_price=p - 50,
                               max_price=p + 50, modal_price=p, arrivals=200 + i % 5, rainfall=0))
    db.add(User(role="admin", name="Admin", phone="9999999999", password_hash=hash_password("admin123")))
    db.commit()
    db.close()


def register(role, phone, lang="en", lat=16.7107, lon=81.0952, name=None):
    client.post("/auth/register", json={"name": name or f"{role}-{phone}", "phone": phone, "password": "secret1", "role": role,
                                         "location": "Eluru", "latitude": lat, "longitude": lon, "language": lang})
    r = client.post("/auth/login", json={"phone": phone, "password": "secret1"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def login(phone, password):
    r = client.post("/auth/login", json={"phone": phone, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def window(days=20):
    return {"from": str(date.today()), "to": str(date.today() + timedelta(days=days))}


def post_listing(h, qty=100, quality="A", crop="paddy", days=15):
    w = window(days)
    r = client.post("/farmer/listings", headers=h, json={"crop": crop, "quantity_quintals": qty, "quality": quality,
                                                         "sell_from": w["from"], "sell_to": w["to"]})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def post_requirement(h, qty=80, price=2500, quality="B", crop="paddy", lat=None, lon=None):
    w = window(25)
    body = {"crop": crop, "quantity_quintals": qty, "offered_price": price, "quality_required": quality,
            "buy_from": w["from"], "buy_to": w["to"]}
    if lat is not None:
        body.update(latitude=lat, longitude=lon)
    r = client.post("/buyer/requirements", headers=h, json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]
