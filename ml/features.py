"""Data normalization / feature extraction (patent FIG. 5, engine 510)."""
import numpy as np
import pandas as pd

LAGS = (1, 7, 14)
FEATURE_COLS = (
    ["modal_price", "min_price", "max_price", "arrivals", "rainfall"]
    + [f"price_lag_{l}" for l in LAGS]
    + ["arr_lag_1", "price_roll_7", "price_roll_30", "price_std_7", "arr_roll_7", "arr_roll_30",
       "rain_roll_7", "month", "doy_sin", "doy_cos", "spread", "momentum", "arr_ratio", "demand_index",
       "crop_code", "market_code"]
)


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["market", "crop", "date"]).reset_index(drop=True)
    g = df.groupby(["market", "crop"], group_keys=False)
    for l in LAGS:
        df[f"price_lag_{l}"] = g["modal_price"].shift(l)
    df["arr_lag_1"] = g["arrivals"].shift(1)
    roll = lambda col, w, f="mean": g[col].transform(lambda s: getattr(s.rolling(w, min_periods=max(3, w // 3)), f)())
    df["price_roll_7"], df["price_roll_30"] = roll("modal_price", 7), roll("modal_price", 30)
    df["price_std_7"] = roll("modal_price", 7, "std")
    df["arr_roll_7"], df["arr_roll_30"] = roll("arrivals", 7), roll("arrivals", 30)
    df["rain_roll_7"] = roll("rainfall", 7)
    df["month"] = df["date"].dt.month
    doy = df["date"].dt.dayofyear
    df["doy_sin"], df["doy_cos"] = np.sin(2 * np.pi * doy / 365), np.cos(2 * np.pi * doy / 365)
    df["spread"] = (df["max_price"] - df["min_price"]) / df["modal_price"]
    df["momentum"] = df["price_roll_7"] / df["price_roll_30"]
    df["arr_ratio"] = df["arr_roll_7"] / df["arr_roll_30"].replace(0, np.nan)
    # Demand proxy: prices rising while arrivals fall => high demand (0..1). Same formula in price_service fallback.
    df["demand_index"] = (0.5 + (df["momentum"] - 1) * 2.5 - (df["arr_ratio"] - 1)).clip(0, 1)
    return df


def make_encoders(df: pd.DataFrame) -> dict:
    return {"crop": {c: i for i, c in enumerate(sorted(df["crop"].unique()))},
            "market": {m: i for i, m in enumerate(sorted(df["market"].unique()))}}


def encode(df: pd.DataFrame, enc: dict) -> pd.DataFrame:
    df = df.copy()
    df["crop_code"] = df["crop"].map(enc["crop"])
    df["market_code"] = df["market"].map(enc["market"])
    return df


def build_training_set(raw: pd.DataFrame, horizon: int = 7):
    """Returns (dataset with targets, encoders). Targets: price and demand `horizon` days ahead."""
    enc = make_encoders(raw)
    df = encode(add_features(raw), enc)
    g = df.groupby(["market", "crop"], group_keys=False)
    df["target_price"] = g["modal_price"].shift(-horizon)
    df["target_return"] = df["target_price"] / df["modal_price"] - 1   # model predicts % change, not absolute price
    df["target_demand"] = g["demand_index"].shift(-horizon)
    df = df.dropna(subset=FEATURE_COLS + ["target_price", "target_demand"]).reset_index(drop=True)
    return df, enc


def time_split(df: pd.DataFrame, test_frac: float = 0.2):
    """Time-based split (never random): last `test_frac` of the dates are held out."""
    cut = df["date"].sort_values().iloc[int(len(df) * (1 - test_frac))]
    return df[df["date"] < cut], df[df["date"] >= cut]
