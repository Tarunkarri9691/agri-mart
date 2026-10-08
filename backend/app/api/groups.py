"""Farmer groups: pool produce from nearby farmers to unlock bigger buyers and cheaper transport per quintal."""
from datetime import date
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import FarmerGroup, FarmerListing, GroupMember, User
from ..security import require_role
from ..services.matching import QUALITY_RANK
from ..services.recommender import recommend

router = APIRouter(prefix="/groups", tags=["groups"])


def _members(db: Session, group: FarmerGroup):
    rows = db.query(GroupMember).filter(GroupMember.group_id == group.id).all()
    return [db.get(FarmerListing, m.listing_id) for m in rows]


def _pooled(group: FarmerGroup, listings: list[FarmerListing]):
    start, end = max(l.sell_from for l in listings), min(l.sell_to for l in listings)
    if end < start:
        raise HTTPException(400, "Members' selling windows do not overlap")
    qty = sum(l.quantity_quintals for l in listings)
    worst = min(listings, key=lambda l: QUALITY_RANK[l.quality]).quality
    lat = sum(l.latitude * l.quantity_quintals for l in listings) / qty   # quantity-weighted collection point
    lon = sum(l.longitude * l.quantity_quintals for l in listings) / qty
    return SimpleNamespace(id=None, crop=group.crop, quantity_quintals=qty, quality=worst, latitude=lat,
                           longitude=lon, sell_from=start, sell_to=end, location="Group pickup point")


def _check(db, group_id, user) -> FarmerGroup:
    g = db.get(FarmerGroup, group_id)
    if not g:
        raise HTTPException(404, "Group not found")
    return g


def _add(db, g, user, listing_id):
    l = db.get(FarmerListing, listing_id)
    if not l or l.farmer_id != user.id or l.crop != g.crop:
        raise HTTPException(400, "Choose one of your own listings for this group's crop")
    if db.query(GroupMember).filter_by(group_id=g.id, listing_id=l.id).first():
        raise HTTPException(409, "Listing already in this group")
    db.add(GroupMember(group_id=g.id, farmer_id=user.id, listing_id=l.id))
    db.commit()


@router.post("", status_code=201)
def create_group(body: schemas.GroupCreate, user: User = Depends(require_role("farmer")), db: Session = Depends(get_db)):
    g = FarmerGroup(name=body.name, crop=body.crop, leader_id=user.id)
    db.add(g)
    db.commit()
    _add(db, g, user, body.listing_id)
    return {"id": g.id, "name": g.name, "crop": g.crop}


@router.get("")
def list_groups(crop: str | None = None, user: User = Depends(require_role("farmer")), db: Session = Depends(get_db)):
    q = db.query(FarmerGroup)
    if crop:
        q = q.filter(FarmerGroup.crop == crop.lower())
    out = []
    for g in q.all():
        ls = _members(db, g)
        out.append({"id": g.id, "name": g.name, "crop": g.crop, "members": len(ls),
                    "total_quintals": sum(l.quantity_quintals for l in ls),
                    "mine": any(l.farmer_id == user.id for l in ls)})
    return out


@router.post("/{group_id}/join")
def join(group_id: int, body: schemas.GroupJoin, user: User = Depends(require_role("farmer")), db: Session = Depends(get_db)):
    _add(db, _check(db, group_id, user), user, body.listing_id)
    return {"status": "joined"}


@router.get("/{group_id}/recommendations")
def group_recommendations(group_id: int, user: User = Depends(require_role("farmer")), db: Session = Depends(get_db)):
    """Best buyers for the pooled lot, and the gain versus each member selling alone."""
    g = _check(db, group_id, user)
    listings = _members(db, g)
    if not any(l.farmer_id == user.id for l in listings):
        raise HTTPException(403, "Join the group to see its recommendations")
    pooled = recommend(db, _pooled(g, listings), persist=False)
    solo_total = 0.0
    solo = []
    for l in listings:
        r = recommend(db, l, persist=False)
        best = r[0]["net_realization"] if r else 0.0
        solo_total += best
        solo.append({"listing_id": l.id, "farmer_id": l.farmer_id, "quantity": l.quantity_quintals, "best_solo_net": best})
    pooled_net = pooled[0]["net_realization"] if pooled else 0.0
    total_q = sum(l.quantity_quintals for l in listings)
    shares = [{**s, "pooled_share": round(pooled_net * s["quantity"] / total_q, 2)} for s in solo]
    return {"group": {"id": g.id, "name": g.name, "crop": g.crop, "members": len(listings), "total_quintals": total_q},
            "recommendations": pooled[:5], "solo_total_net": round(solo_total, 2), "pooled_net": pooled_net,
            "pooling_gain": round(pooled_net - solo_total, 2), "member_shares": shares}
