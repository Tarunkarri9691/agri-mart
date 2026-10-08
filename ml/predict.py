"""Inference API used by the backend (patent engine 150)."""
import joblib
import pandas as pd

from ._train_common import DEFAULT_HORIZON, HORIZONS, MODELS_DIR
from .conformal import offsets_for
from .explain import top_drivers
from .features import FEATURE_COLS, add_features, encode

_cache: dict = {}


def _load(name: str):
    if name not in _cache:
        _cache[name] = joblib.load(MODELS_DIR / f"{name}.joblib")
    return _cache[name]


def reload():
    _cache.clear()


def _latest_row(history: pd.DataFrame, enc: dict, crop: str, market: str) -> pd.DataFrame:
    if crop not in enc["crop"] or market not in enc["market"]:
        raise KeyError(f"{crop}/{market} not seen in training")
    df = encode(add_features(history), enc)
    row = df.iloc[[-1]][FEATURE_COLS]
    if row.isna().any(axis=None):
        raise ValueError("not enough history for features")
    return row


def predict_price(history: pd.DataFrame, crop: str, market: str, horizon: int = DEFAULT_HORIZON,
                  explain: bool = False, row: pd.DataFrame | None = None) -> dict:
    """history: recent rows for ONE crop+market (columns: date, market, crop, min/max/modal_price, arrivals, rainfall).
    Returns price plus an 80% conformal interval [low, high]."""
    art = _load(f"price_h{horizon}")
    row = row if row is not None else _latest_row(history, art["encoders"], crop, market)
    cur = float(row["modal_price"].iloc[0])
    ret = float(art["model"].predict(row)[0])
    lo, hi = offsets_for(art["conformal"], crop)
    out = {"price": cur * (1 + ret), "low": cur * (1 + ret + lo), "high": cur * (1 + ret + hi),
           "horizon_days": horizon, "drivers": []}
    try:
        d = _load("demand_ensemble")
        out["demand_index"] = float(min(1.0, max(0.0, d["model"].predict(row)[0])))
    except FileNotFoundError:
        out["demand_index"] = float(row["demand_index"].iloc[0])
    if explain:
        out["drivers"] = top_drivers(art["model"], row)
    return out


def predict_curve(history: pd.DataFrame, crop: str, market: str, horizons=HORIZONS) -> list[dict]:
    """Multi-horizon forecast used for the sell-now-vs-wait advice."""
    return [predict_price(history, crop, market, h) for h in horizons]
