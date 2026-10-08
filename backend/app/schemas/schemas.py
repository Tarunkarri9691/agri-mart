from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UserCreate(BaseModel):
    name: str
    phone: str
    password: str = Field(min_length=6)
    role: Literal["farmer", "buyer"]
    location: str = ""
    latitude: float
    longitude: float
    language: Literal["en", "te"] = "en"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    phone: str
    role: str
    location: str
    latitude: float
    longitude: float
    language: str = "en"
    reliability: float = 4.0
    rating_count: int = 0


class LoginIn(BaseModel):
    phone: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ListingCreate(BaseModel):
    crop: str
    quantity_quintals: float = Field(gt=0)
    quality: Literal["A", "B", "C"] = "B"
    location: str = ""
    latitude: Optional[float] = None   # defaults to farmer profile location
    longitude: Optional[float] = None
    sell_from: date
    sell_to: date

    @field_validator("crop")
    @classmethod
    def _crop(cls, v):
        return v.strip().lower()

    @model_validator(mode="after")
    def _dates(self):
        if self.sell_to < self.sell_from:
            raise ValueError("sell_to must be on or after sell_from")
        return self


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    crop: str
    quantity_quintals: float
    quality: str
    location: str
    latitude: float
    longitude: float
    sell_from: date
    sell_to: date
    status: str


class RequirementCreate(BaseModel):
    crop: str
    quantity_quintals: float = Field(gt=0)
    offered_price: float = Field(gt=0, description="Rs per quintal")
    quality_required: Literal["A", "B", "C"] = "C"
    location: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    buy_from: date
    buy_to: date

    @field_validator("crop")
    @classmethod
    def _crop(cls, v):
        return v.strip().lower()

    @model_validator(mode="after")
    def _dates(self):
        if self.buy_to < self.buy_from:
            raise ValueError("buy_to must be on or after buy_from")
        return self


class RequirementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    crop: str
    quantity_quintals: float
    offered_price: float
    quality_required: str
    location: str
    latitude: float
    longitude: float
    buy_from: date
    buy_to: date
    status: str


class MarketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    district: str
    latitude: float
    longitude: float
    crops: str


class PricePredictionOut(BaseModel):
    crop: str
    market: str
    horizon_days: int
    predicted_price: float
    low: float
    high: float
    demand_index: float
    volatility: float
    source: str


class Recommendation(BaseModel):
    rank: int
    candidate_type: str
    candidate_id: int
    name: str
    location: str
    distance_km: float
    predicted_price: float
    price_used: float
    quantity_sold: float
    gross_value: float
    transport_cost: float
    commission: float
    expected_loss: float
    net_realization: float
    compatibility: float
    risk_score: float
    risk_tag: str
    score: float
    opportunity_id: Optional[int] = None
    net_low: Optional[float] = None
    net_high: Optional[float] = None
    trips: int = 1
    msp: Optional[float] = None
    below_msp: bool = False
    details: dict[str, Any] = {}


class OfferCreate(BaseModel):
    listing_id: int
    requirement_id: Optional[int] = None   # required when a farmer starts the offer
    price: float = Field(gt=0, description="Rs per quintal")
    quantity: float = Field(gt=0)
    message: str = ""


class OfferRespond(BaseModel):
    action: Literal["accept", "reject", "counter"]
    price: Optional[float] = Field(default=None, gt=0)
    quantity: Optional[float] = Field(default=None, gt=0)
    message: str = ""


class PaymentIn(BaseModel):
    method: Literal["upi", "bank", "cash"]
    reference: str = ""
    amount: Optional[float] = Field(default=None, gt=0)


class DisputeIn(BaseModel):
    reason: str = Field(min_length=5)


class RatingIn(BaseModel):
    score: int = Field(ge=1, le=5)
    comment: str = ""


class OfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    listing_id: int
    requirement_id: Optional[int]
    farmer_id: int
    buyer_id: int
    farmer_name: str = ""
    buyer_name: str = ""
    crop: str = ""
    price: float
    quantity: float
    status: str
    last_actor: str
    message: str
    history: list[Any] = []
    payment_status: str
    payment_method: str
    payment_reference: str
    payment_amount: float
    dispute_reason: str
    can_respond: bool = False


class GroupCreate(BaseModel):
    name: str
    crop: str
    listing_id: int

    @field_validator("crop")
    @classmethod
    def _crop(cls, v):
        return v.strip().lower()


class GroupJoin(BaseModel):
    listing_id: int


class AlertCreate(BaseModel):
    crop: str
    market: Optional[str] = None
    threshold_pct: float = Field(default=5.0, gt=0, le=50)

    @field_validator("crop")
    @classmethod
    def _crop(cls, v):
        return v.strip().lower()


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    crop: str
    market_id: Optional[int]
    threshold_pct: float
    active: bool


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: str
    title: str
    body: str
    delivery: str
    read: bool
    created_at: Any


class MarketIn(BaseModel):
    name: str
    district: str = ""
    latitude: float
    longitude: float
    crops: str = "paddy,maize,chilli,cotton,banana"
