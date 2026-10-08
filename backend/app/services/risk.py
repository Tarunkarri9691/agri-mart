"""Risk analysis (patent step 260). Score in [0,1] -> low / moderate / high tag (FIG. 3, ref 320)."""
from .. import config


def _clip(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def risk_tag(score: float) -> str:
    if score < config.RISK_LOW_MAX:
        return "low"
    if score < config.RISK_MODERATE_MAX:
        return "moderate"
    return "high"


def risk_assessment(volatility: float, demand_index: float, distance_km: float,
                    reliability: float, spoilage_rate: float) -> dict:
    """volatility = coefficient of variation of recent prices (0.25 -> max risk)."""
    comps = {
        "price_volatility": _clip(volatility / 0.25),
        "demand_uncertainty": _clip(1 - demand_index),
        "distance": _clip(distance_km / 400.0),
        "buyer_reliability": _clip((5 - _clip(reliability, 1, 5)) / 4),
        "spoilage": _clip(spoilage_rate / 0.10),
    }
    w = config.RISK_WEIGHTS
    score = round(sum(w[k] * v for k, v in comps.items()), 4)
    return {
        "score": score,
        "tag": risk_tag(score),
        "components": {k: round(v, 3) for k, v in comps.items()},
        "weights": w,
    }
