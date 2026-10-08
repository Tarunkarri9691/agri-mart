"""Offers, negotiation, payment tracking, disputes, ratings, and outcome feedback."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import config, schemas
from ..database import get_db
from ..models import BuyerRequirement, FarmerListing, Offer, Opportunity, Outcome, Rating, User
from ..security import get_current_user
from ..services.notifier import notify

router = APIRouter(prefix="/offers", tags=["offers"])
ACTIVE = ("pending", "accepted")


def _out(o: Offer, user: User) -> schemas.OfferOut:
    can = o.status == "pending" and o.last_actor != user.role and user.id in (o.farmer_id, o.buyer_id)
    d = schemas.OfferOut.model_validate(o)
    d.farmer_name, d.buyer_name, d.crop, d.can_respond = o.farmer.name, o.buyer.name, o.listing.crop, can
    return d


def _get(db: Session, offer_id: int, user: User) -> Offer:
    o = db.get(Offer, offer_id)
    if not o or user.id not in (o.farmer_id, o.buyer_id):
        raise HTTPException(404, "Offer not found")
    return o


def _other(o: Offer, user: User) -> User:
    return o.buyer if user.id == o.farmer_id else o.farmer


def _log(o: Offer, actor: str, action: str, price=None, qty=None):
    o.history = [*(o.history or []), {"at": datetime.utcnow().isoformat(timespec="seconds"), "by": actor,
                                      "action": action, "price": price, "quantity": qty}]
    o.updated_at = datetime.utcnow()


def _reopen(db: Session, o: Offer):
    if o.listing.status in ("reserved", "sold"):
        o.listing.status = "open"
    if o.requirement_id:
        req = db.get(BuyerRequirement, o.requirement_id)
        if req and req.status != "open":
            req.status = "open"


@router.post("", response_model=schemas.OfferOut, status_code=201)
def create_offer(body: schemas.OfferCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in ("farmer", "buyer"):
        raise HTTPException(403, "Only farmers and buyers can make offers")
    listing = db.get(FarmerListing, body.listing_id)
    if not listing or listing.status != "open":
        raise HTTPException(404, "Listing not available")
    if body.quantity > listing.quantity_quintals:
        raise HTTPException(400, "Quantity exceeds what the farmer has listed")
    if user.role == "farmer":
        if listing.farmer_id != user.id:
            raise HTTPException(403, "Not your listing")
        req = db.get(BuyerRequirement, body.requirement_id) if body.requirement_id else None
        if not req or req.status != "open" or req.crop != listing.crop:
            raise HTTPException(400, "A matching open buyer requirement is required")
        buyer_id, farmer_id = req.buyer_id, user.id
    else:
        buyer_id, farmer_id = user.id, listing.farmer_id
        if body.requirement_id:
            req = db.get(BuyerRequirement, body.requirement_id)
            if not req or req.buyer_id != user.id:
                raise HTTPException(400, "Requirement does not belong to you")
    if db.query(Offer).filter(Offer.listing_id == listing.id, Offer.buyer_id == buyer_id, Offer.status.in_(ACTIVE)).first():
        raise HTTPException(409, "There is already an active offer between these two parties for this listing")
    o = Offer(listing_id=listing.id, requirement_id=body.requirement_id, farmer_id=farmer_id, buyer_id=buyer_id,
              price=body.price, quantity=body.quantity, message=body.message, last_actor=user.role, history=[])
    _log(o, user.role, "offer", body.price, body.quantity)
    db.add(o)
    db.commit()
    notify(db, _other(o, user), "offer_received", crop=listing.crop, price=round(o.price), qty=o.quantity)
    return _out(o, user)


@router.get("", response_model=list[schemas.OfferOut])
def my_offers(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Offer).filter((Offer.farmer_id == user.id) | (Offer.buyer_id == user.id)).order_by(Offer.id.desc())
    return [_out(o, user) for o in q.all()]


@router.post("/{offer_id}/respond", response_model=schemas.OfferOut)
def respond(offer_id: int, body: schemas.OfferRespond, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    o = _get(db, offer_id, user)
    if o.status != "pending" or o.last_actor == user.role:
        raise HTTPException(409, "It is not your turn to respond to this offer")
    other = _other(o, user)
    if body.action == "accept":
        o.status = "accepted"
        o.listing.status = "reserved"
        if o.requirement_id:
            req = db.get(BuyerRequirement, o.requirement_id)
            if req:
                req.status = "reserved"
        _log(o, user.role, "accept")
        notify(db, other, "offer_accepted", crop=o.listing.crop)
    elif body.action == "reject":
        o.status = "rejected"
        _log(o, user.role, "reject")
        notify(db, other, "offer_rejected", crop=o.listing.crop)
    else:
        if body.price is None:
            raise HTTPException(400, "A counter offer needs a price")
        qty = body.quantity or o.quantity
        if qty > o.listing.quantity_quintals:
            raise HTTPException(400, "Quantity exceeds what the farmer has listed")
        o.price, o.quantity, o.last_actor = body.price, qty, user.role
        if body.message:
            o.message = body.message
        _log(o, user.role, "counter", o.price, o.quantity)
        notify(db, other, "offer_countered", crop=o.listing.crop, price=round(o.price), qty=o.quantity)
    db.commit()
    return _out(o, user)


@router.post("/{offer_id}/cancel", response_model=schemas.OfferOut)
def cancel(offer_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    o = _get(db, offer_id, user)
    if o.status not in ACTIVE or o.payment_status != "none":
        raise HTTPException(409, "This offer can no longer be cancelled")
    o.status = "cancelled"
    _reopen(db, o)
    _log(o, user.role, "cancel")
    db.commit()
    return _out(o, user)


@router.post("/{offer_id}/payment", response_model=schemas.OfferOut)
def mark_paid(offer_id: int, body: schemas.PaymentIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Buyer records that payment was made (UPI / bank / cash reference). Money moves outside the platform."""
    o = _get(db, offer_id, user)
    if user.id != o.buyer_id or o.status != "accepted" or o.payment_status != "none":
        raise HTTPException(409, "Only the buyer can record payment on an accepted offer")
    o.payment_status, o.payment_method, o.payment_reference = "paid", body.method, body.reference
    o.payment_amount = body.amount or round(o.price * o.quantity, 2)
    _log(o, "buyer", "payment_marked")
    db.commit()
    notify(db, o.farmer, "payment_paid", crop=o.listing.crop, amount=round(o.payment_amount))
    return _out(o, user)


@router.post("/{offer_id}/confirm-payment", response_model=schemas.OfferOut)
def confirm_payment(offer_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    o = _get(db, offer_id, user)
    if user.id != o.farmer_id or o.status != "accepted" or o.payment_status != "paid":
        raise HTTPException(409, "Only the farmer can confirm a payment the buyer has recorded")
    o.payment_status, o.status, o.completed_at = "confirmed", "completed", datetime.utcnow()
    o.listing.status = "sold"
    if o.requirement_id:
        req = db.get(BuyerRequirement, o.requirement_id)
        if req:
            req.status = "filled"
    _record_outcome(db, o)
    _log(o, "farmer", "payment_confirmed")
    db.commit()
    notify(db, o.buyer, "deal_completed", crop=o.listing.crop)
    notify(db, o.farmer, "deal_completed", crop=o.listing.crop)
    return _out(o, user)


def _record_outcome(db: Session, o: Offer):
    """Decision feedback: where did the chosen buyer rank in the last recommendation, and how did the deal price compare?"""
    opp = None
    for cand in db.query(Opportunity).filter(Opportunity.listing_id == o.listing_id).all():
        m = cand.match_details
        if m.get("candidate_type") == "buyer" and m.get("candidate_id") == o.requirement_id:
            opp = cand
    rec_price = opp.model_output.get("price_used") if opp else None
    gap = round((o.price - rec_price) / rec_price * 100, 2) if rec_price else None
    db.add(Outcome(offer_id=o.id, listing_id=o.listing_id, crop=o.listing.crop, chosen_rank=opp.rank if opp else None,
                   recommended_price=rec_price, actual_price=o.price, quantity=o.quantity, price_gap_pct=gap))


@router.post("/{offer_id}/dispute", response_model=schemas.OfferOut)
def dispute(offer_id: int, body: schemas.DisputeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    o = _get(db, offer_id, user)
    if o.status != "accepted":
        raise HTTPException(409, "Disputes can be opened on accepted, not-yet-completed deals")
    o.status, o.dispute_reason = "disputed", body.reason
    _log(o, user.role, "dispute")
    db.commit()
    notify(db, _other(o, user), "dispute_opened", crop=o.listing.crop)
    return _out(o, user)


@router.post("/{offer_id}/rate")
def rate(offer_id: int, body: schemas.RatingIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    o = _get(db, offer_id, user)
    if o.status != "completed":
        raise HTTPException(409, "You can rate the other party after the deal is completed")
    ratee = _other(o, user)
    if db.query(Rating).filter_by(offer_id=o.id, rater_id=user.id).first():
        raise HTTPException(409, "You have already rated this deal")
    db.add(Rating(offer_id=o.id, rater_id=user.id, ratee_id=ratee.id, score=body.score, comment=body.comment))
    db.flush()
    total, n = db.query(func.sum(Rating.score), func.count(Rating.id)).filter(Rating.ratee_id == ratee.id).one()
    w = config.RATING_PRIOR_WEIGHT
    ratee.reliability = round((config.RATING_PRIOR * w + (total or 0)) / (w + n), 3)   # Bayesian average
    ratee.rating_count = n
    db.commit()
    return {"ratee": ratee.name, "reliability": ratee.reliability, "rating_count": n}
