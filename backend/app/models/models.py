"""Database tables (patent FIG. 1 ref 140/142, FIG. 3 record = Opportunity)."""
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(10))  # farmer | buyer | admin
    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    location: Mapped[str] = mapped_column(String(120), default="")
    latitude: Mapped[float] = mapped_column(Float, default=0.0)
    longitude: Mapped[float] = mapped_column(Float, default=0.0)
    reliability: Mapped[float] = mapped_column(Float, default=4.0)  # Bayesian-average rating 1-5
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    language: Mapped[str] = mapped_column(String(5), default="en")  # en | te (notifications)


class FarmerListing(Base):  # patent step 210
    __tablename__ = "farmer_listings"
    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    crop: Mapped[str] = mapped_column(String(40), index=True)
    quantity_quintals: Mapped[float] = mapped_column(Float)
    quality: Mapped[str] = mapped_column(String(1), default="B")
    location: Mapped[str] = mapped_column(String(120), default="")
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    sell_from: Mapped[date] = mapped_column(Date)
    sell_to: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10), default="open")  # open | reserved | sold
    last_best_net: Mapped[float | None] = mapped_column(Float, nullable=True)
    farmer: Mapped[User] = relationship()


class BuyerRequirement(Base):  # patent step 215
    __tablename__ = "buyer_requirements"
    id: Mapped[int] = mapped_column(primary_key=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    crop: Mapped[str] = mapped_column(String(40), index=True)
    quantity_quintals: Mapped[float] = mapped_column(Float)
    offered_price: Mapped[float] = mapped_column(Float)  # Rs per quintal
    quality_required: Mapped[str] = mapped_column(String(1), default="C")
    location: Mapped[str] = mapped_column(String(120), default="")
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    buy_from: Mapped[date] = mapped_column(Date)
    buy_to: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10), default="open")
    buyer: Mapped[User] = relationship()


class Market(Base):
    __tablename__ = "markets"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    district: Mapped[str] = mapped_column(String(80), default="")
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    crops: Mapped[str] = mapped_column(String(300), default="")  # comma separated


class MarketPrice(Base):  # patent FIG.1 ref 142
    __tablename__ = "market_prices"
    __table_args__ = (UniqueConstraint("market_id", "crop", "date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id"), index=True)
    crop: Mapped[str] = mapped_column(String(40), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    min_price: Mapped[float] = mapped_column(Float)
    max_price: Mapped[float] = mapped_column(Float)
    modal_price: Mapped[float] = mapped_column(Float)
    arrivals: Mapped[float] = mapped_column(Float, default=0.0)
    rainfall: Mapped[float] = mapped_column(Float, default=0.0)


class Prediction(Base):
    __tablename__ = "predictions"
    id: Mapped[int] = mapped_column(primary_key=True)
    crop: Mapped[str] = mapped_column(String(40), index=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    horizon_days: Mapped[int] = mapped_column(Integer)
    predicted_price: Mapped[float] = mapped_column(Float)
    demand_index: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(30))


class Opportunity(Base):
    """Crop Selling Opportunity Record (patent FIG. 3, ref 300)."""
    __tablename__ = "opportunities"
    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("farmer_listings.id"), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)  # 320
    risk_tag: Mapped[str] = mapped_column(String(10))                                # 320
    crop_details: Mapped[dict] = mapped_column(JSON)                                 # 330
    match_details: Mapped[dict] = mapped_column(JSON)                                 # 340
    model_output: Mapped[dict] = mapped_column(JSON)                                 # 350


class Offer(Base):
    """Negotiation + deal record between a farmer listing and a buyer requirement."""
    __tablename__ = "offers"
    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("farmer_listings.id"), index=True)
    requirement_id: Mapped[int | None] = mapped_column(ForeignKey("buyer_requirements.id"), nullable=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    price: Mapped[float] = mapped_column(Float)              # Rs per quintal (current terms)
    quantity: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(12), default="pending", index=True)
    # pending | accepted | rejected | cancelled | disputed | completed
    last_actor: Mapped[str] = mapped_column(String(6))       # farmer | buyer - who made the current terms
    message: Mapped[str] = mapped_column(Text, default="")
    history: Mapped[list] = mapped_column(JSON, default=list)
    payment_status: Mapped[str] = mapped_column(String(10), default="none")  # none | paid | confirmed
    payment_method: Mapped[str] = mapped_column(String(10), default="")
    payment_reference: Mapped[str] = mapped_column(String(80), default="")
    payment_amount: Mapped[float] = mapped_column(Float, default=0.0)
    dispute_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    listing: Mapped[FarmerListing] = relationship()
    farmer: Mapped[User] = relationship(foreign_keys=[farmer_id])
    buyer: Mapped[User] = relationship(foreign_keys=[buyer_id])


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (UniqueConstraint("offer_id", "rater_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id"), index=True)
    rater_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    ratee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    score: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Outcome(Base):
    """Decision feedback: what the farmer actually did vs what the system recommended."""
    __tablename__ = "outcomes"
    id: Mapped[int] = mapped_column(primary_key=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id"), unique=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("farmer_listings.id"), index=True)
    crop: Mapped[str] = mapped_column(String(40))
    chosen_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)   # rank the chosen buyer had in the last recommendation
    recommended_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[float] = mapped_column(Float)
    price_gap_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FarmerGroup(Base):
    __tablename__ = "farmer_groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    leader_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    crop: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("group_id", "listing_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("farmer_groups.id"), index=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    listing_id: Mapped[int] = mapped_column(ForeignKey("farmer_listings.id"))


class PriceAlert(Base):
    __tablename__ = "price_alerts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    crop: Mapped[str] = mapped_column(String(40))
    market_id: Mapped[int | None] = mapped_column(ForeignKey("markets.id"), nullable=True)  # None = all markets
    threshold_pct: Mapped[float] = mapped_column(Float, default=5.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_notified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(20), default="inapp")
    delivery: Mapped[str] = mapped_column(String(10), default="inapp")  # inapp | sent | failed | logged
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    method: Mapped[str] = mapped_column(String(8))
    path: Mapped[str] = mapped_column(String(200))
    status_code: Mapped[int] = mapped_column(Integer)
    ip: Mapped[str] = mapped_column(String(45), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
