"""Backtest engine shared by the headline, ablation and weight-tuning experiments.
It re-uses the production services (transport, net realization, risk, ranking) so the numbers describe the real system.

Method (no look-ahead):
  1. Train the price model ONLY on data before a cutoff date.
  2. For random (date, crop, farm location, quantity) cases after the cutoff, predict each mandi's price `horizon` days ahead
     from information available on that date.
  3. A strategy picks a mandi. Its realized outcome uses the ACTUAL price `horizon` days later, and the true transport cost.
Note: only mandis are simulated (no real buyer-offer history exists), so this measures price-forecast + logistics value."""
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app import config  # noqa: E402
from app.services.net_realization import compute_net_realization, spoilage_loss_rate  # noqa: E402
from app.services.risk import risk_assessment  # noqa: E402
from app.services.transport import road_distance_km, transport_cost, travel_hours  # noqa: E402

from ml._train_common import load_data  # noqa: E402
from ml.data_ingestion.markets import MARKETS  # noqa: E402
from ml.ensemble import Ensemble  # noqa: E402
from ml.features import FEATURE_COLS, add_features, encode, make_encoders  # noqa: E402

MARKET_XY = {n: (lat, lon) for n, _, lat, lon in MARKETS}


@dataclass
class Strategy:
    name: str
    use_forecast: bool = True      # False -> assume today's price persists
    use_transport: bool = True     # False -> rank on price only
    use_risk: bool = True
    use_demand: bool = True
    w_net: float = config.RANK_W_NET
    w_compat: float = config.RANK_W_COMPAT
    w_risk: float = config.RANK_W_RISK
    nearest_only: bool = False
    highest_current_price: bool = False


def prepare(horizon: int = 7, cutoff_frac: float = 0.7, seed: int = 0, use_cache: bool = True):
    """Returns (table of per-(date,market,crop) features + predictions + realized future price, cutoff date).
    The trained-before-cutoff predictions are cached; delete ml/experiments/results/_table_h*.pkl after changing data."""
    cache = Path(__file__).parent / "results" / f"_table_h{horizon}.pkl"
    if use_cache and cache.exists():
        return pd.read_pickle(cache)
    raw = load_data()
    enc = make_encoders(raw)
    df = encode(add_features(raw), enc)
    g = df.groupby(["market", "crop"], group_keys=False)
    df["future_price"] = g["modal_price"].shift(-horizon)
    df["target_return"] = df["future_price"] / df["modal_price"] - 1
    df = df.dropna(subset=FEATURE_COLS + ["future_price"]).reset_index(drop=True)
    cutoff = df["date"].sort_values().iloc[int(len(df) * cutoff_frac)]
    train = df[df["date"] < cutoff - pd.Timedelta(days=horizon)]   # outcome windows must also end before the cutoff
    model = Ensemble(seed).fit(train[FEATURE_COLS], train["target_return"])
    test = df[df["date"] >= cutoff].copy()
    test["pred_price"] = test["modal_price"] * (1 + model.predict(test[FEATURE_COLS]))
    cache.parent.mkdir(exist_ok=True)
    pd.to_pickle((test, cutoff), cache)
    return test, cutoff


def simulate(table: pd.DataFrame, strategies: list[Strategy], n: int = 1500, seed: int = 0, horizon: int = 7) -> pd.DataFrame:
    """Returns per-case realized net per quintal for each strategy plus the oracle (best hindsight mandi)."""
    rng = np.random.default_rng(seed)
    dates = np.array(sorted(table["date"].unique()))
    crops = sorted(table["crop"].unique())
    by_key = {k: g.set_index("market") for k, g in table.groupby(["date", "crop"])}
    names = list(MARKET_XY)
    rows = []
    while len(rows) < n:
        d, crop = dates[rng.integers(len(dates))], crops[rng.integers(len(crops))]
        snap = by_key.get((pd.Timestamp(d), crop))
        if snap is None or len(snap) < len(names):
            continue
        base = MARKET_XY[names[rng.integers(len(names))]]
        lat, lon = base[0] + rng.normal(0, 0.15), base[1] + rng.normal(0, 0.15)   # farm somewhere near a market
        qty = float(rng.choice([20, 50, 100, 200, 400]))
        cand = []
        for m in names:
            r = snap.loc[m]
            dist = road_distance_km(lat, lon, *MARKET_XY[m])
            hours = travel_hours(dist)
            loss = spoilage_loss_rate(crop, hours)
            tc = transport_cost(dist, qty)
            realized = compute_net_realization(r["future_price"], qty, tc, config.MARKET_COMMISSION_PCT, loss)["net_realization"] / qty
            cand.append({"m": m, "dist": dist, "tc": tc, "loss": loss, "cur": r["modal_price"], "pred": r["pred_price"],
                         "vol": float(r["price_std_7"] / r["price_roll_7"]) if r["price_roll_7"] else 0.1,
                         "demand": float(r["demand_index"]), "realized": realized})
        row = {"date": d, "crop": crop, "qty": qty, "oracle": max(c["realized"] for c in cand)}
        for s in strategies:
            row[s.name] = _choose(s, cand, qty)["realized"]
        rows.append(row)
    return pd.DataFrame(rows)


def _choose(s: Strategy, cand: list[dict], qty: float) -> dict:
    if s.nearest_only:
        return min(cand, key=lambda c: c["dist"])
    if s.highest_current_price:
        return max(cand, key=lambda c: c["cur"])
    scored = []
    for c in cand:
        price = c["pred"] if s.use_forecast else c["cur"]
        tc = c["tc"] if s.use_transport else 0.0
        net = compute_net_realization(price, qty, tc, config.MARKET_COMMISSION_PCT, c["loss"])["net_realization"] / qty
        risk = risk_assessment(c["vol"], c["demand"] if s.use_demand else 0.5, c["dist"], 4.0, c["loss"])["score"] if s.use_risk else 0.0
        scored.append((net, risk, c))
    best_net = max(x[0] for x in scored)
    return max(scored, key=lambda x: s.w_net * (x[0] / best_net if best_net > 0 else 0) + s.w_compat * 0.85 - s.w_risk * x[1])[2]


def bootstrap_ci(x: np.ndarray, reps: int = 2000, seed: int = 0) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    means = [rng.choice(x, len(x)).mean() for _ in range(reps)]
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))
