"""Orchestrates the FIG. 2 pipeline: match -> predict -> transport -> net realization -> risk -> rank."""
import math
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from .. import config
from ..models import BuyerRequirement, FarmerListing, Market, MarketPrice, Opportunity
from . import matching, price_service
from .net_realization import compute_net_realization, spoilage_loss_rate
from .ranking import rank_candidates
from .risk import risk_assessment
from .transport import haversine_km, road_distance_km, transport_cost, travel_hours, trips_needed


@dataclass
class Candidate:
    kind: str                      # "buyer" | "market"
    id: int
    name: str
    location: str
    lat: float
    lon: float
    compatibility: float
    commission_pct: float
    reliability: float = 4.0
    offered_price: Optional[float] = None
    required_qty: Optional[float] = None
    market_id: Optional[int] = None  # market whose price signal is used


def _nearest_market_id(db: Session, crop: str, lat: float, lon: float) -> Optional[int]:
    ids = [r[0] for r in db.query(MarketPrice.market_id).filter(MarketPrice.crop == crop).distinct()]
    best, best_d = None, 1e12
    for m in db.query(Market).filter(Market.id.in_(ids)).all() if ids else []:
        d = haversine_km(lat, lon, m.latitude, m.longitude)
        if d < best_d:
            best, best_d = m.id, d
    return best


def _bbox(lat: float, lon: float, radius_km: float):
    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * max(0.2, math.cos(math.radians(lat))))
    return lat - dlat, lat + dlat, lon - dlon, lon + dlon


def build_candidates(db: Session, listing: FarmerListing) -> list[Candidate]:
    cands: list[Candidate] = []
    r = config.MAX_MATCH_RADIUS_KM
    la0, la1, lo0, lo1 = _bbox(listing.latitude, listing.longitude, r)
    reqs = (db.query(BuyerRequirement)
            .filter(BuyerRequirement.crop == listing.crop, BuyerRequirement.status == "open",
                    BuyerRequirement.latitude.between(la0, la1), BuyerRequirement.longitude.between(lo0, lo1)).all())
    for r in reqs:
        c = matching.compatibility(listing.crop, listing.quantity_quintals, listing.quality,
                                   listing.sell_from, listing.sell_to,
                                   r.crop, r.quantity_quintals, r.quality_required, r.buy_from, r.buy_to)
        if c >= config.MIN_COMPATIBILITY:
            cands.append(Candidate("buyer", r.id, r.buyer.name, r.location or r.buyer.location, r.latitude,
                                   r.longitude, c, config.DIRECT_COMMISSION_PCT, r.buyer.reliability,
                                   r.offered_price, r.quantity_quintals,
                                   _nearest_market_id(db, listing.crop, r.latitude, r.longitude)))
    for m in db.query(Market).all():
        if haversine_km(listing.latitude, listing.longitude, m.latitude, m.longitude) > config.MAX_MATCH_RADIUS_KM:
            continue
        c = matching.market_compatibility(listing.crop, m.crops)
        if c >= config.MIN_COMPATIBILITY:
            cands.append(Candidate("market", m.id, m.name, m.district, m.latitude, m.longitude, c,
                                   config.MARKET_COMMISSION_PCT, 4.0, None, None, m.id))
    return cands


def recommend(db: Session, listing: FarmerListing, persist: bool = True) -> list[dict]:
    signals: dict = {}

    def signal(mid):
        if mid not in signals:
            signals[mid] = price_service.predict(db, listing.crop, mid, persist=persist, explain=False) if mid else None
        return signals[mid]

    results = []
    for c in build_candidates(db, listing):
        sig = signal(c.market_id)
        if c.kind == "market":
            if not sig:
                continue
            price, qty = sig["price"], listing.quantity_quintals
        else:
            price = c.offered_price or (sig["price"] if sig else None)
            if not price:
                continue
            qty = min(listing.quantity_quintals, c.required_qty)
        dist = road_distance_km(listing.latitude, listing.longitude, c.lat, c.lon)
        hours = travel_hours(dist)
        loss_rate = spoilage_loss_rate(listing.crop, hours)
        tc = transport_cost(dist, qty)
        nr = compute_net_realization(price, qty, tc, c.commission_pct, loss_rate)
        # price range only exists for forecast-based prices; a buyer's fixed offer has no price uncertainty
        if c.kind == "market":
            lo_p, hi_p = sig["low"], sig["high"]
        else:
            lo_p = hi_p = price
        net_low = compute_net_realization(lo_p, qty, tc, c.commission_pct, loss_rate)["net_realization"]
        net_high = compute_net_realization(hi_p, qty, tc, c.commission_pct, loss_rate)["net_realization"]
        # forecast uncertainty (conformal interval) feeds the risk score together with recent price swings
        eff_vol = (0.5 * sig["volatility"] + sig["uncertainty"]) if (sig and c.kind == "market") else (sig["volatility"] if sig else 0.1)
        risk = risk_assessment(eff_vol, sig["demand_index"] if sig else 0.5, dist, c.reliability, loss_rate)
        msp = config.MSP.get(listing.crop)
        results.append({
            "candidate_type": c.kind, "candidate_id": c.id, "name": c.name, "location": c.location,
            "distance_km": dist, "travel_hours": round(hours, 1),
            "predicted_price": sig["price"] if sig else price, "price_used": round(price, 2),
            "quantity_sold": qty, **nr, "net_low": net_low, "net_high": net_high, "trips": trips_needed(qty),
            "msp": msp, "below_msp": bool(msp and price < msp), "signal_market_id": c.market_id,
            "compatibility": c.compatibility,
            "risk_score": risk["score"], "risk_tag": risk["tag"],
            "details": {"risk": risk, "price_source": sig["source"] if sig else "buyer_offer",
                        "demand_index": sig["demand_index"] if sig else None,
                        "volatility": sig["volatility"] if sig else None,
                        "price_interval": [sig["low"], sig["high"]] if sig else None,
                        "price_drivers": sig["drivers"] if sig else [],
                        "weights": {"net": config.RANK_W_NET, "compat": config.RANK_W_COMPAT,
                                    "risk": config.RANK_W_RISK}},
        })
    ranked = rank_candidates(results, listing.quantity_quintals)
    if persist:
        _persist(db, listing, ranked)
    return ranked


def _persist(db: Session, listing: FarmerListing, ranked: list[dict]):
    db.query(Opportunity).filter(Opportunity.listing_id == listing.id).delete()
    for item in ranked:
        opp = Opportunity(
            listing_id=listing.id, rank=item["rank"], risk_tag=item["risk_tag"],
            crop_details={"crop": listing.crop, "quantity_quintals": listing.quantity_quintals,
                          "quality": listing.quality, "location": listing.location},
            match_details={k: item[k] for k in ("candidate_type", "candidate_id", "name", "location",
                                                "distance_km", "compatibility")},
            model_output={k: v for k, v in item.items()
                          if k not in ("candidate_type", "candidate_id", "name", "location")},
        )
        db.add(opp)
        db.flush()
        item["opportunity_id"] = opp.id
    db.commit()
