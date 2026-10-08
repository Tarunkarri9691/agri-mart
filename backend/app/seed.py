"""Seed demo data: markets, price history, admin, a demo farmer and buyers.
Run:  python -m app.seed         (idempotent)"""
from datetime import date, timedelta

import pandas as pd

from . import config
from .database import Base, SessionLocal, engine
from .models import BuyerRequirement, Market, MarketPrice, PriceAlert, User
from .security import hash_password

from ml.data_ingestion.markets import CROPS, MARKETS  # noqa: E402
from ml.data_ingestion.generate_synthetic import DATA_PATH, generate  # noqa: E402

BUYERS = [  # name, phone, location, lat, lon, reliability
    ("Godavari Rice Mills", "9000000001", "Tadepalligudem", 16.8135, 81.5270, 4.6),
    ("Krishna Agro Traders", "9000000002", "Vijayawada", 16.5062, 80.6480, 4.2),
    ("Konaseema Foods", "9000000003", "Kakinada", 16.9891, 82.2475, 4.0),
    ("Guntur Spice Exports", "9000000004", "Guntur", 16.3067, 80.4365, 4.8),
    ("Coastal Poultry Feeds", "9000000005", "Bhimavaram", 16.5449, 81.5212, 3.5),
    ("Delta Cotton Ginning", "9000000006", "Eluru", 16.7107, 81.0952, 4.1),
    ("Vizag Fresh Mart", "9000000007", "Visakhapatnam", 17.6868, 83.2185, 3.8),
]
BUYER_CROPS = {0: "paddy", 1: "maize", 2: "banana", 3: "chilli", 4: "maize", 5: "cotton", 6: "banana"}


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if db.query(Market).count():
        print("Already seeded.")
        return
    for name, district, lat, lon in MARKETS:
        db.add(Market(name=name, district=district, latitude=lat, longitude=lon, crops=",".join(CROPS)))
    db.commit()

    if not DATA_PATH.exists():
        generate()
    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    df = df[df["date"] >= df["date"].max() - pd.Timedelta(days=365)]
    ids = {m.name: m.id for m in db.query(Market).all()}
    rows = [{"market_id": ids[r.market], "crop": r.crop, "date": r.date.date(), "min_price": r.min_price,
             "max_price": r.max_price, "modal_price": r.modal_price, "arrivals": r.arrivals,
             "rainfall": r.rainfall} for r in df.itertuples()]
    db.bulk_insert_mappings(MarketPrice, rows)

    db.add(User(role="admin", name="Admin", phone="9999999999", password_hash=hash_password("admin123")))
    db.add(User(role="farmer", name="Demo Farmer", phone="8000000001", password_hash=hash_password("farmer123"),
                location="Eluru", latitude=16.7107, longitude=81.0952, language="te"))
    db.flush()
    farmer = db.query(User).filter_by(phone="8000000001").one()
    db.add(PriceAlert(user_id=farmer.id, crop="paddy", threshold_pct=3.0))
    today = date.today()
    for i, (name, phone, loc, lat, lon, rel) in enumerate(BUYERS):
        u = User(role="buyer", name=name, phone=phone, password_hash=hash_password("buyer123"),
                 location=loc, latitude=lat, longitude=lon, reliability=rel)
        db.add(u)
        db.flush()
        crop = BUYER_CROPS[i]
        base = df[df["crop"] == crop]["modal_price"].tail(30).mean()
        db.add(BuyerRequirement(buyer_id=u.id, crop=crop, quantity_quintals=100 + 40 * i,
                                offered_price=round(base * (0.97 + 0.02 * (i % 4)), 0),
                                quality_required="B" if i % 2 else "C", location=loc, latitude=lat,
                                longitude=lon, buy_from=today, buy_to=today + timedelta(days=30)))
    db.commit()
    print(f"Seeded {len(MARKETS)} markets, {len(rows)} price rows, {len(BUYERS)} buyers.")
    print("Logins -> farmer 8000000001/farmer123 | buyer 9000000001/buyer123 | admin 9999999999/admin123")


if __name__ == "__main__":
    main()
