"""Synthetic mandi data (Rs/quintal) so the project runs without API access.
Schema matches the cleaned Agmarknet data:  date, market, crop, min_price, max_price, modal_price, arrivals, rainfall
Run:  python -m ml.data_ingestion.generate_synthetic"""
from pathlib import Path

import numpy as np
import pandas as pd

from .markets import CROPS, MARKETS

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "market_prices.csv"
BASE = {"paddy": 2200, "maize": 2100, "chilli": 14000, "cotton": 6800, "banana": 1800}
PHASE = {"paddy": 0.5, "maize": 1.5, "chilli": 3.0, "cotton": 4.5, "banana": 2.2}
VOL = {"paddy": 0.004, "maize": 0.006, "chilli": 0.012, "cotton": 0.007, "banana": 0.02}


def generate(years: int = 3, seed: int = 42, end: pd.Timestamp | None = None) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    end = (end or pd.Timestamp.today().normalize())
    dates = pd.date_range(end=end, periods=365 * years, freq="D")
    t = np.arange(len(dates))
    doy = dates.dayofyear.values
    monsoon = np.exp(-((doy - 220) / 45.0) ** 2)  # rain peaks around August
    frames = []
    for crop in CROPS:
        seasonal = 1 + 0.12 * np.sin(2 * np.pi * doy / 365 + PHASE[crop])
        trend = 1 + 0.0002 * t
        for name, _, _, _ in MARKETS:
            offset = rng.uniform(0.95, 1.06)
            shock = np.zeros(len(t))
            for i in range(1, len(t)):                       # AR(1) market shocks
                shock[i] = 0.97 * shock[i - 1] + rng.normal(0, VOL[crop])
            rain = np.clip(rng.gamma(2, 6, len(t)) * monsoon, 0, 120)
            modal = BASE[crop] * seasonal * trend * offset * np.exp(shock) * (1 + 0.0005 * rain)
            arrivals = np.clip(300 * (1 - 4 * shock) * (1 + 0.2 * np.cos(2 * np.pi * doy / 365)) *
                               rng.uniform(0.8, 1.2, len(t)), 20, None)
            frames.append(pd.DataFrame({
                "date": dates, "market": name, "crop": crop,
                "min_price": (modal * rng.uniform(0.90, 0.97, len(t))).round(0),
                "max_price": (modal * rng.uniform(1.03, 1.10, len(t))).round(0),
                "modal_price": modal.round(0), "arrivals": arrivals.round(1), "rainfall": rain.round(1)}))
    df = pd.concat(frames, ignore_index=True)
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA_PATH, index=False)
    print(f"Wrote {len(df):,} rows -> {DATA_PATH}")
    return df


if __name__ == "__main__":
    generate()
