"""Ranking: Score = w1*NetRealization(norm) + w2*Compatibility - w3*Risk (patent step 260)."""
from .. import config


def rank_candidates(items: list[dict], listing_quantity: float) -> list[dict]:
    if not items:
        return []
    per_q = [i["net_realization"] / max(listing_quantity, 1e-9) for i in items]
    hi = max(per_q)
    for item, v in zip(items, per_q):
        # ratio to the best option (1.0 = best); gentler than min-max so tiny gaps are not exaggerated
        norm = 1.0 if hi <= 0 else max(0.0, v / hi)
        item["net_normalized"] = round(norm, 4)
        item["score"] = round(config.RANK_W_NET * norm
                              + config.RANK_W_COMPAT * item["compatibility"]
                              - config.RANK_W_RISK * item["risk_score"], 4)
    items.sort(key=lambda i: i["score"], reverse=True)
    for n, item in enumerate(items, 1):
        item["rank"] = n
    return items
