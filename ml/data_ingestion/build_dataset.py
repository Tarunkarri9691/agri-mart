"""Merge real prices + weather (+ optional arrivals file) -> clean -> ml/data/market_prices.csv
    python -m ml.data_ingestion.build_dataset
Inputs (all optional except prices):
    ml/data/raw_agmarknet.csv   prices      (fetch_agmarknet / import_csv)
    ml/data/weather.csv         rainfall    (fetch_weather)
    ml/data/arrivals.csv        arrivals    columns: date,market,crop,arrivals (quintals)"""
from pathlib import Path

import pandas as pd

from .clean import clean
from .generate_synthetic import DATA_PATH

DATA = Path(__file__).resolve().parents[1] / "data"


def merge(prices: pd.DataFrame, weather: pd.DataFrame | None = None, arrivals: pd.DataFrame | None = None) -> pd.DataFrame:
    prices = prices.copy()
    prices["date"] = pd.to_datetime(prices["date"])
    prices["market"] = prices["market"].str.strip().str.title()
    if weather is not None:
        w = weather.copy()
        w["date"] = pd.to_datetime(w["date"])
        w["market"] = w["market"].str.strip().str.title()
        prices = prices.drop(columns=["rainfall"], errors="ignore").merge(
            w[["date", "market", "rainfall"]], on=["date", "market"], how="left")
    if arrivals is not None:
        a = arrivals.copy()
        a["date"] = pd.to_datetime(a["date"])
        a["market"] = a["market"].str.strip().str.title()
        prices = prices.drop(columns=["arrivals"], errors="ignore").merge(
            a[["date", "market", "crop", "arrivals"]], on=["date", "market", "crop"], how="left")
    return clean(prices)


if __name__ == "__main__":
    prices = pd.read_csv(DATA / "raw_agmarknet.csv")
    weather = pd.read_csv(DATA / "weather.csv") if (DATA / "weather.csv").exists() else None
    arrivals = pd.read_csv(DATA / "arrivals.csv") if (DATA / "arrivals.csv").exists() else None
    out = merge(prices, weather, arrivals)
    out.to_csv(DATA_PATH, index=False)
    print(f"{len(out):,} rows -> {DATA_PATH}  (weather: {weather is not None}, arrivals: {arrivals is not None})")
