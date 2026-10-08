from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import FarmerListing, Opportunity, User
from ..security import require_role
from ..services import price_service
from ..services.recommender import recommend
from ..services.timing import timing_advice

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _own_listing(db: Session, listing_id: int, user: User) -> FarmerListing:
    listing = db.get(FarmerListing, listing_id)
    if not listing or listing.farmer_id != user.id:
        raise HTTPException(404, "Listing not found")
    return listing


@router.get("/{listing_id}", response_model=list[schemas.Recommendation])
def recommendations(listing_id: int, user: User = Depends(require_role("farmer")), db: Session = Depends(get_db)):
    """Ranked buyers/markets for a listing. Recomputed on every call so new prices/requirements are picked up."""
    return recommend(db, _own_listing(db, listing_id, user))


@router.get("/{listing_id}/explain")
def explain(listing_id: int, rank: int = 1, user: User = Depends(require_role("farmer")),
            db: Session = Depends(get_db)):
    """Explainable breakdown (patent ref 350 / 450 / 550): price, cost and risk drivers for one result."""
    listing = _own_listing(db, listing_id, user)
    opp = db.query(Opportunity).filter_by(listing_id=listing.id, rank=rank).first()
    if not opp:
        recommend(db, listing)
        opp = db.query(Opportunity).filter_by(listing_id=listing.id, rank=rank).first()
    if not opp:
        raise HTTPException(404, "No recommendation with that rank")
    m = opp.model_output
    d = m["details"]
    drivers = d["price_drivers"]
    if not drivers and d["price_source"] == "ml_ensemble" and m.get("signal_market_id"):   # SHAP computed on demand (slow)
        sig = price_service.predict(db, listing.crop, m["signal_market_id"], persist=False, explain=True)
        drivers = sig["drivers"] if sig else []
    return {
        "opportunity_id": opp.id, "rank": opp.rank, "timestamp": opp.timestamp, "risk_tag": opp.risk_tag,
        "crop_details": opp.crop_details, "match_details": opp.match_details,
        "price_factors": {"predicted_price": m["predicted_price"], "price_used": m["price_used"],
                          "source": d["price_source"], "demand_index": d["demand_index"],
                          "volatility": d["volatility"], "top_drivers": drivers},
        "cost_factors": {k: m[k] for k in ("gross_value", "transport_cost", "commission", "expected_loss",
                                           "net_realization", "distance_km", "travel_hours")},
        "risk_factors": d["risk"],
        "ranking": {"score": m["score"], "net_normalized": m["net_normalized"],
                    "compatibility": m["compatibility"], "weights": d["weights"]},
    }


@router.get("/{listing_id}/timing")
def timing(listing_id: int, user: User = Depends(require_role("farmer")), db: Session = Depends(get_db)):
    """Sell now or wait? Compares today's best net realization with waiting 3/7/14 days (forecast, storage cost and loss)."""
    listing = _own_listing(db, listing_id, user)
    advice = timing_advice(db, listing, recommend(db, listing, persist=False))
    if not advice:
        raise HTTPException(404, "No matching buyers or markets yet")
    return advice
