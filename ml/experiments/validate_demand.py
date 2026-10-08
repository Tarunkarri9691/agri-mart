"""Does the demand index actually predict price moves?  Rank correlation between today's demand index and the NEXT 7-day
price change, plus mean return of the top vs bottom quartile.   python -m ml.experiments.validate_demand"""
import numpy as np
import pandas as pd

from .._train_common import load_data
from ..features import add_features


def evaluate(raw: pd.DataFrame, horizon: int = 7) -> dict:
    df = add_features(raw)
    g = df.groupby(["market", "crop"], group_keys=False)
    df["future_return"] = g["modal_price"].shift(-horizon) / df["modal_price"] - 1
    df = df.dropna(subset=["demand_index", "future_return"])
    rho = float(df["demand_index"].rank().corr(df["future_return"].rank()))
    q_hi, q_lo = df["demand_index"].quantile([0.75, 0.25])
    top, bot = df[df["demand_index"] >= q_hi]["future_return"], df[df["demand_index"] <= q_lo]["future_return"]
    return {"n": int(len(df)), "spearman_rho": round(rho, 4), "top_quartile_mean_return_pct": round(float(top.mean()) * 100, 3),
            "bottom_quartile_mean_return_pct": round(float(bot.mean()) * 100, 3),
            "verdict": "useful signal" if rho > 0.05 and top.mean() > bot.mean() else "weak/no signal - treat the demand index as a heuristic"}


if __name__ == "__main__":
    for k, v in evaluate(load_data()).items():
        print(f"{k}: {v}")
