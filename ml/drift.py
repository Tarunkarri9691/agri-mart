"""Model drift check: re-score the deployed model on the most recent rows with known outcomes and compare
the error to the error measured at training time."""
import numpy as np
import pandas as pd

from ._train_common import DEFAULT_HORIZON
from .features import FEATURE_COLS, add_features, encode
from .metrics import mape
from .predict import _load


def check_drift(history: pd.DataFrame, horizon: int = DEFAULT_HORIZON, recent_days: int = 45, factor: float = 1.5) -> dict:
    """history: price rows for all markets/crops (as in market_prices.csv). Flags drift if recent MAPE > factor x training MAPE."""
    art = _load(f"price_h{horizon}")
    df = encode(add_features(history), art["encoders"])
    g = df.groupby(["market", "crop"], group_keys=False)
    df["target_price"] = g["modal_price"].shift(-horizon)
    df = df.dropna(subset=FEATURE_COLS + ["target_price"])
    df = df[df["date"] >= df["date"].max() - pd.Timedelta(days=recent_days)]
    if len(df) < 50:
        return {"drift": False, "reason": "not enough recent data", "n": int(len(df))}
    pred = df["modal_price"].values * (1 + art["model"].predict(df[FEATURE_COLS]))
    recent = mape(df["target_price"].values, pred)
    base = float(art["metrics"]["ensemble"]["MAPE"])
    return {"drift": bool(recent > factor * base), "recent_mape": round(recent, 3), "training_mape": round(base, 3),
            "factor": factor, "n": int(len(df))}
