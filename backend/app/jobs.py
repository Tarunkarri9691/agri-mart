"""Background jobs (APScheduler). Each returns a small dict so admins can also trigger them via POST /admin/jobs/{name}."""
import logging
import threading
from datetime import date, datetime, timedelta

import pandas as pd

from . import config
from .database import SessionLocal
from .models import FarmerListing, Market, MarketPrice, PriceAlert, User
from .services import price_service
from .services.notifier import notify
from .services.recommender import recommend
from .ws import manager

log = logging.getLogger(__name__)


def recompute_listings() -> dict:
    """Re-rank every open listing with the latest prices; notify + push to the farmer when the best option moved."""
    changed = n = 0
    with SessionLocal() as db:
        for l in db.query(FarmerListing).filter(FarmerListing.status == "open", FarmerListing.sell_to >= date.today()).all():
            ranked = recommend(db, l, persist=True)
            if not ranked:
                continue
            n += 1
            best, old = ranked[0], l.last_best_net
            if old and abs(best["net_realization"] - old) / old * 100 >= config.RECOMPUTE_CHANGE_PCT:
                changed += 1
                notify(db, l.farmer, "best_option_changed", crop=l.crop, name=best["name"],
                       net=round(best["net_realization"]), old=round(old))
                manager.push(l.farmer_id, {"type": "recommendation_update", "listing_id": l.id})
            l.last_best_net = best["net_realization"]
            db.commit()
    return {"recomputed": n, "notified": changed}


def check_price_alerts() -> dict:
    sent = 0
    with SessionLocal() as db:
        for a in db.query(PriceAlert).filter(PriceAlert.active.is_(True)).all():
            if a.last_notified_at and datetime.utcnow() - a.last_notified_at < timedelta(hours=24):
                continue
            markets = [db.get(Market, a.market_id)] if a.market_id else db.query(Market).all()
            for m in markets:
                sig = price_service.predict(db, a.crop, m.id, persist=False, explain=False)
                cur = price_service.latest_price(db, a.crop, m.id)
                if not sig or not cur:
                    continue
                pct = (sig["price"] - cur) / cur * 100
                if abs(pct) >= a.threshold_pct:
                    notify(db, db.get(User, a.user_id), "price_move", crop=a.crop, market=m.name,
                           pct=f"{pct:+.1f}", price=round(sig["price"]))
                    a.last_notified_at = datetime.utcnow()
                    db.commit()
                    sent += 1
                    break
    return {"alerts_sent": sent}


def sync_prices() -> dict:
    """Pull the latest Agmarknet prices (needs DATA_GOV_API_KEY) and upsert them for known markets."""
    if not config.DATA_GOV_API_KEY:
        return {"skipped": "DATA_GOV_API_KEY not set"}
    from ml.data_ingestion.fetch_agmarknet import fetch
    df = fetch()
    added = 0
    with SessionLocal() as db:
        ids = {m.name.lower(): m.id for m in db.query(Market).all()}
        for r in df.itertuples():
            mid = ids.get(str(r.market).lower())
            if not mid or db.query(MarketPrice).filter_by(market_id=mid, crop=r.crop, date=r.date.date()).first():
                continue
            last = (db.query(MarketPrice).filter_by(market_id=mid, crop=r.crop).order_by(MarketPrice.date.desc()).first())
            db.add(MarketPrice(market_id=mid, crop=r.crop, date=r.date.date(), min_price=r.min_price, max_price=r.max_price,
                               modal_price=r.modal_price, arrivals=(last.arrivals if last else 0.0), rainfall=0.0))
            added += 1
        db.commit()
    return {"fetched": len(df), "added": added}


def _retrain_async():
    from .api.admin import _retrain
    threading.Thread(target=_retrain, daemon=True).start()


def check_model_drift(auto_retrain: bool = True) -> dict:
    try:
        from ml.drift import check_drift
        with SessionLocal() as db:
            cutoff = date.today() - timedelta(days=200)
            names = {m.id: m.name for m in db.query(Market).all()}
            rows = db.query(MarketPrice).filter(MarketPrice.date >= cutoff).all()
            df = pd.DataFrame([{"date": r.date, "market": names[r.market_id], "crop": r.crop, "min_price": r.min_price,
                                "max_price": r.max_price, "modal_price": r.modal_price, "arrivals": r.arrivals,
                                "rainfall": r.rainfall} for r in rows])
            result = check_drift(df)
            if result.get("drift"):
                for admin in db.query(User).filter(User.role == "admin").all():
                    notify(db, admin, "model_drift", recent=result["recent_mape"], base=result["training_mape"])
                if auto_retrain:
                    _retrain_async()
        return result
    except FileNotFoundError:
        return {"skipped": "no trained model"}
    except Exception as exc:
        log.warning("drift check failed: %s", exc)
        return {"error": str(exc)}


def weekly_retrain() -> dict:
    _retrain_async()
    return {"status": "retraining started"}


def start_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    sch = BackgroundScheduler(timezone="Asia/Kolkata")
    sch.add_job(recompute_listings, "interval", minutes=60, id="recompute")
    sch.add_job(check_price_alerts, "interval", minutes=60, id="alerts")
    sch.add_job(sync_prices, "cron", hour=6, minute=30, id="sync")
    sch.add_job(check_model_drift, "cron", hour=3, minute=0, id="drift")
    sch.add_job(weekly_retrain, "cron", day_of_week="sun", hour=2, minute=0, id="retrain")
    sch.start()
    return sch
