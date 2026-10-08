from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import BuyerRequirement, FarmerListing, User
from ..security import require_role
from ..services import matching
from ..services.transport import road_distance_km

router = APIRouter(prefix="/buyer", tags=["buyer"])


@router.post("/requirements", response_model=schemas.RequirementOut, status_code=201)
def create_requirement(body: schemas.RequirementCreate, user: User = Depends(require_role("buyer")),
                       db: Session = Depends(get_db)):
    data = body.model_dump()
    data["latitude"] = data["latitude"] if data["latitude"] is not None else user.latitude
    data["longitude"] = data["longitude"] if data["longitude"] is not None else user.longitude
    data["location"] = data["location"] or user.location
    req = BuyerRequirement(**data, buyer_id=user.id)
    db.add(req)
    db.commit()
    return req


@router.get("/requirements", response_model=list[schemas.RequirementOut])
def my_requirements(user: User = Depends(require_role("buyer")), db: Session = Depends(get_db)):
    return (db.query(BuyerRequirement).filter(BuyerRequirement.buyer_id == user.id)
            .order_by(BuyerRequirement.id.desc()).all())


@router.get("/matches")
def matched_farmers(user: User = Depends(require_role("buyer")), db: Session = Depends(get_db)):
    """Open farmer listings that fit each of this buyer's requirements."""
    out = []
    for r in db.query(BuyerRequirement).filter(BuyerRequirement.buyer_id == user.id).all():
        for l in db.query(FarmerListing).filter(FarmerListing.crop == r.crop, FarmerListing.status == "open"):
            c = matching.compatibility(l.crop, l.quantity_quintals, l.quality, l.sell_from, l.sell_to,
                                       r.crop, r.quantity_quintals, r.quality_required, r.buy_from, r.buy_to)
            if c > 0:
                out.append({"requirement_id": r.id, "listing_id": l.id, "farmer": l.farmer.name,
                            "phone": l.farmer.phone, "crop": l.crop, "quantity_quintals": l.quantity_quintals,
                            "quality": l.quality, "location": l.location, "compatibility": c,
                            "distance_km": road_distance_km(l.latitude, l.longitude, r.latitude, r.longitude)})
    return sorted(out, key=lambda x: -x["compatibility"])
