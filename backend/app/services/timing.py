"""Sell now vs wait: compares today's best net realization with the expected net after waiting 3/7/14 days
(forecast price - storage cost - storage loss), using the 80% interval as the downside case."""
from datetime import date

from .. import config
from . import price_service
from .net_realization import compute_net_realization


def decide_timing(sell_now_net: float, options: list[dict]) -> dict:
    """options: [{days, net, net_low, net_high}] for waiting alternatives. Wait only if the expected gain is meaningful
    AND the pessimistic case is not much worse than selling now."""
    if not options or sell_now_net <= 0:
        return {"decision": "sell_now", "wait_days": 0, "expected_gain_pct": 0.0, "downside_pct": 0.0,
                "reason": "No later selling date improves on selling now."}
    best = max(options, key=lambda o: o["net"])
    gain = (best["net"] - sell_now_net) / sell_now_net * 100
    downside = (sell_now_net - best["net_low"]) / sell_now_net * 100
    if gain >= config.WAIT_MIN_GAIN_PCT and downside <= config.WAIT_MAX_DOWNSIDE_PCT:
        return {"decision": "wait", "wait_days": best["days"], "expected_gain_pct": round(gain, 2),
                "downside_pct": round(downside, 2),
                "reason": f"Waiting {best['days']} days is expected to add {gain:.1f}% and the pessimistic case is "
                          f"only {max(downside, 0):.1f}% below selling now."}
    why = (f"Best waiting option adds only {gain:.1f}% (need {config.WAIT_MIN_GAIN_PCT:.0f}%)." if gain < config.WAIT_MIN_GAIN_PCT
           else f"Waiting could gain {gain:.1f}% but the pessimistic case is {downside:.1f}% worse than selling now.")
    return {"decision": "sell_now", "wait_days": 0, "expected_gain_pct": round(gain, 2),
            "downside_pct": round(downside, 2), "reason": why}


def timing_advice(db, listing, ranked: list[dict]) -> dict | None:
    if not ranked:
        return None
    top = ranked[0]
    market_item = next((r for r in ranked if r["candidate_type"] == "market" and r.get("signal_market_id")), None)
    out = {"sell_now": {"name": top["name"], "net_realization": top["net_realization"]}, "options": [],
           "wait_candidate": None}
    if not market_item:
        out.update(decide_timing(top["net_realization"], []))
        return out
    out["wait_candidate"] = market_item["name"]
    qty = market_item["quantity_sold"]
    gross = market_item["gross_value"] or 1.0
    commission_pct = market_item["commission"] / gross
    loss_rate = market_item["expected_loss"] / gross
    store_loss = config.STORAGE_LOSS_PER_DAY.get(listing.crop, config.DEFAULT_STORAGE_LOSS_PER_DAY)
    days_available = (listing.sell_to - date.today()).days
    options = []
    for h in config.HORIZONS:
        if h > days_available:
            continue
        sig = price_service.predict(db, listing.crop, market_item["signal_market_id"], persist=False, horizon=h, explain=False)
        if not sig:
            continue

        def net(p):
            n = compute_net_realization(p, qty, market_item["transport_cost"], commission_pct, loss_rate + store_loss * h)
            return round(n["net_realization"] - config.STORAGE_COST_PER_QUINTAL_DAY * qty * h, 2)

        options.append({"days": h, "price": sig["price"], "price_low": sig["low"], "price_high": sig["high"],
                        "net": net(sig["price"]), "net_low": net(sig["low"]), "net_high": net(sig["high"])})
    out["options"] = options
    out.update(decide_timing(top["net_realization"], options))
    return out
