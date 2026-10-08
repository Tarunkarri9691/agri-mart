"""Estimated net realization (patent step 250 / ref 540)."""
from .. import config


def spoilage_loss_rate(crop: str, travel_hours: float) -> float:
    per_day = config.SPOILAGE_PER_DAY.get(crop.lower(), config.DEFAULT_SPOILAGE_PER_DAY)
    return min(per_day * travel_hours / 24.0, 0.5)


def compute_net_realization(price_per_quintal: float, quantity: float, transport: float,
                            commission_pct: float, loss_rate: float) -> dict:
    """Net = (price x qty) - transport - commission - expected spoilage loss."""
    gross = price_per_quintal * quantity
    commission = gross * commission_pct
    expected_loss = gross * loss_rate
    net = gross - transport - commission - expected_loss
    return {
        "gross_value": round(gross, 2),
        "transport_cost": round(transport, 2),
        "commission": round(commission, 2),
        "expected_loss": round(expected_loss, 2),
        "net_realization": round(net, 2),
    }
