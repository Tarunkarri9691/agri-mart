from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import FarmerListing, User
from ..security import require_role

router = APIRouter(prefix="/farmer", tags=["farmer"])


@router.post("/listings", response_model=schemas.ListingOut, status_code=201)
def create_listing(body: schemas.ListingCreate, user: User = Depends(require_role("farmer")),
                   db: Session = Depends(get_db)):
    data = body.model_dump()
    data["latitude"] = data["latitude"] if data["latitude"] is not None else user.latitude
    data["longitude"] = data["longitude"] if data["longitude"] is not None else user.longitude
    data["location"] = data["location"] or user.location
    listing = FarmerListing(**data, farmer_id=user.id)
    db.add(listing)
    db.commit()
    return listing


@router.get("/listings", response_model=list[schemas.ListingOut])
def my_listings(user: User = Depends(require_role("farmer")), db: Session = Depends(get_db)):
    return (db.query(FarmerListing).filter(FarmerListing.farmer_id == user.id)
            .order_by(FarmerListing.id.desc()).all())
