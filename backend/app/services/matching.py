"""Buyer/market compatibility matching (patent step 240 / ref 530)."""
from datetime import date

QUALITY_RANK = {"A": 3, "B": 2, "C": 1}
W_QUALITY, W_QUANTITY, W_DATE = 0.3, 0.4, 0.3


def quality_score(offered: str, required: str | None) -> float:
    if not required:
        return 1.0
    diff = QUALITY_RANK[offered] - QUALITY_RANK[required]
    return 1.0 if diff >= 0 else (0.5 if diff == -1 else 0.0)


def quantity_coverage(available: float, needed: float) -> float:
    return 1.0 if needed <= 0 else min(1.0, available / needed)


def date_overlap(a_from: date, a_to: date, b_from: date, b_to: date) -> float:
    start, end = max(a_from, b_from), min(a_to, b_to)
    if end < start:
        return 0.0
    overlap = (end - start).days + 1
    shortest = min((a_to - a_from).days + 1, (b_to - b_from).days + 1)
    return min(1.0, overlap / shortest)


def compatibility(listing_crop, listing_qty, listing_quality, sell_from, sell_to,
                  req_crop, req_qty, req_quality, buy_from, buy_to) -> float:
    """Crop must match and dates must overlap; otherwise the opportunity is infeasible (0)."""
    if listing_crop.lower() != req_crop.lower():
        return 0.0
    d = date_overlap(sell_from, sell_to, buy_from, buy_to)
    if d == 0.0:
        return 0.0
    q = quality_score(listing_quality, req_quality)
    c = quantity_coverage(listing_qty, req_qty)
    return round(W_QUALITY * q + W_QUANTITY * c + W_DATE * d, 4)


def market_compatibility(crop: str, market_crops: str) -> float:
    """Mandis accept any quantity/quality of crops they trade; slightly below a perfect direct match."""
    crops = [c.strip().lower() for c in market_crops.split(",") if c.strip()]
    return 0.85 if crop.lower() in crops else 0.0
