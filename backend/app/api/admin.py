"""Admin dashboard: overview + data-quality alerts, users, markets, disputes, retraining, job triggers."""
import json
import subprocess
import sys
from datetime import date, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import config, schemas
from ..database import get_db
from ..models import (AuditLog, BuyerRequirement, FarmerListing, Market, MarketPrice, Offer, Outcome, User)
from ..security import require_role
from ..services.notifier import notify

router = APIRouter(prefix="/admin", tags=["admin"])
admin_only = require_role("admin")


def _retrain():
    for module in ("ml.train_price", "ml.train_demand"):
        p = subprocess.run([sys.executable, "-m", module], cwd=config.REPO_ROOT, capture_output=True, text=True)
        print(p.stdout[-800:], p.stderr[-800:])
        if p.returncode != 0:
            return
    from ml import predict as ml_predict
    ml_predict.reload()  # next prediction uses the new models


@router.post("/retrain", status_code=202)
def retrain(background: BackgroundTasks, user: User = Depends(admin_only)):
    """Retrain price (3/7/14-day) + demand models in the background (takes minutes)."""
    background.add_task(_retrain)
    return {"status": "retraining started"}


@router.post("/jobs/{name}")
def run_job(name: str, user: User = Depends(admin_only)):
    """Run a scheduled job now: recompute | alerts | sync | drift."""
    from .. import jobs
    fn = {"recompute": jobs.recompute_listings, "alerts": jobs.check_price_alerts,
          "sync": jobs.sync_prices, "drift": jobs.check_model_drift}.get(name)
    if not fn:
        raise HTTPException(404, "Unknown job")
    return fn()


def data_quality(db: Session) -> list[dict]:
    """Stale series, missing days and impossible prices."""
    issues = []
    today = date.today()
    names = {m.id: m.name for m in db.query(Market).all()}
    for mid, crop, last, n60 in (db.query(MarketPrice.market_id, MarketPrice.crop, func.max(MarketPrice.date),
                                          func.count(MarketPrice.id))
                                 .filter(MarketPrice.date >= today - timedelta(days=60))
                                 .group_by(MarketPrice.market_id, MarketPrice.crop).all()):
        if (today - last).days > 3:
            issues.append({"type": "stale", "market": names.get(mid), "crop": crop, "detail": f"last price {last}"})
        if n60 < 45:
            issues.append({"type": "missing_days", "market": names.get(mid), "crop": crop, "detail": f"{n60}/60 days present"})
    bad = db.query(func.count(MarketPrice.id)).filter(
        (MarketPrice.modal_price < MarketPrice.min_price * 0.99) | (MarketPrice.modal_price > MarketPrice.max_price * 1.01)).scalar()
    if bad:
        issues.append({"type": "inconsistent", "market": None, "crop": None, "detail": f"{bad} rows with modal outside min-max"})
    return issues


@router.get("/overview")
def overview(user: User = Depends(admin_only), db: Session = Depends(get_db)):
    offers = db.query(Offer.status, func.count(Offer.id)).group_by(Offer.status).all()
    by_status = {s: n for s, n in offers}
    total = sum(by_status.values())
    outcomes = db.query(Outcome).all()
    ranked = [o for o in outcomes if o.chosen_rank]
    gaps = [abs(o.price_gap_pct) for o in outcomes if o.price_gap_pct is not None]
    metrics = {}
    for f in (config.REPO_ROOT / "ml" / "models").glob("*_metrics.json"):
        metrics[f.stem] = json.loads(f.read_text())
    return {
        "users": dict(db.query(User.role, func.count(User.id)).group_by(User.role).all()),
        "listings": dict(db.query(FarmerListing.status, func.count(FarmerListing.id)).group_by(FarmerListing.status).all()),
        "requirements": db.query(func.count(BuyerRequirement.id)).scalar(),
        "offers": by_status,
        "completion_rate": round(by_status.get("completed", 0) / total, 3) if total else None,
        "decision_feedback": {"deals": len(outcomes), "followed_top_recommendation":
                              round(sum(1 for o in ranked if o.chosen_rank == 1) / len(ranked), 3) if ranked else None,
                              "avg_price_gap_pct": round(sum(gaps) / len(gaps), 2) if gaps else None},
        "model_metrics": metrics,
        "data_quality": data_quality(db),
        "open_disputes": by_status.get("disputed", 0),
    }


@router.get("/users")
def users(user: User = Depends(admin_only), db: Session = Depends(get_db)):
    return [{"id": u.id, "name": u.name, "phone": u.phone, "role": u.role, "location": u.location,
             "reliability": u.reliability, "rating_count": u.rating_count} for u in db.query(User).order_by(User.id).all()]


@router.post("/markets", response_model=schemas.MarketOut, status_code=201)
def add_market(body: schemas.MarketIn, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    if db.query(Market).filter(Market.name.ilike(body.name)).first():
        raise HTTPException(409, "Market already exists")
    m = Market(**body.model_dump())
    db.add(m)
    db.commit()
    return m


@router.put("/markets/{market_id}", response_model=schemas.MarketOut)
def update_market(market_id: int, body: schemas.MarketIn, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    m = db.get(Market, market_id)
    if not m:
        raise HTTPException(404, "Market not found")
    for k, v in body.model_dump().items():
        setattr(m, k, v)
    db.commit()
    return m


@router.get("/disputes")
def disputes(user: User = Depends(admin_only), db: Session = Depends(get_db)):
    return [{"offer_id": o.id, "crop": o.listing.crop, "farmer": o.farmer.name, "buyer": o.buyer.name, "price": o.price,
             "quantity": o.quantity, "payment_status": o.payment_status, "payment_reference": o.payment_reference,
             "reason": o.dispute_reason, "history": o.history}
            for o in db.query(Offer).filter(Offer.status == "disputed").all()]


@router.post("/disputes/{offer_id}/resolve")
def resolve(offer_id: int, outcome: str, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    """outcome = complete (payment valid, deal stands) | cancel (deal void, listing reopened)."""
    o = db.get(Offer, offer_id)
    if not o or o.status != "disputed":
        raise HTTPException(404, "No such open dispute")
    if outcome == "complete":
        o.status, o.completed_at, o.payment_status = "completed", datetime.utcnow(), "confirmed"
        o.listing.status = "sold"
    elif outcome == "cancel":
        o.status = "cancelled"
        if o.listing.status in ("reserved", "sold"):
            o.listing.status = "open"
    else:
        raise HTTPException(400, "outcome must be 'complete' or 'cancel'")
    db.commit()
    for party in (o.farmer, o.buyer):
        notify(db, party, "dispute_resolved", crop=o.listing.crop, outcome=outcome)
    return {"offer_id": o.id, "status": o.status}


@router.get("/audit")
def audit(limit: int = 100, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    rows = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(min(limit, 500)).all()
    return [{"at": r.created_at, "user_id": r.user_id, "method": r.method, "path": r.path, "status": r.status_code} for r in rows]
