"""Fetch real mandi prices from data.gov.in (Agmarknet 'Current daily price of commodities').
1. Register at https://data.gov.in and copy your API key.
2. export DATA_GOV_API_KEY=...
3. python -m ml.data_ingestion.fetch_agmarknet
The API returns the most recent arrival date per record, so schedule this DAILY (cron) and append to
ml/data/raw_agmarknet.csv to accumulate history. Check the resource id on data.gov.in if it changes."""
import os
from pathlib import Path

import pandas as pd
import requests

RESOURCE = "9ef84268-d588-465a-a308-a864a43d0070"
URL = f"https://api.data.gov.in/resource/{RESOURCE}"
RAW_PATH = Path(__file__).resolve().parents[1] / "data" / "raw_agmarknet.csv"
COMMODITY_MAP = {"paddy(dhan)(common)": "paddy", "paddy(dhan)": "paddy", "maize": "maize",
                 "dry chillies": "chilli", "chilli": "chilli", "cotton": "cotton", "banana": "banana"}


def fetch(state: str = "Andhra Pradesh", limit: int = 1000) -> pd.DataFrame:
    key = os.environ.get("DATA_GOV_API_KEY")
    if not key:
        raise SystemExit("Set DATA_GOV_API_KEY first.")
    params = {"api-key": key, "format": "json", "limit": limit, "filters[State]": state}
    records = requests.get(URL, params=params, timeout=60).json().get("records", [])
    df = pd.DataFrame(records)
    if df.empty:
        return df
    df.columns = [c.lower() for c in df.columns]
    df["crop"] = df["commodity"].str.lower().map(COMMODITY_MAP)
    df = df.dropna(subset=["crop"])
    out = pd.DataFrame({
        "date": pd.to_datetime(df["arrival_date"], format="%d/%m/%Y"), "market": df["market"].str.title(),
        "crop": df["crop"], "min_price": pd.to_numeric(df["min_price"]), "max_price": pd.to_numeric(df["max_price"]),
        "modal_price": pd.to_numeric(df["modal_price"]), "arrivals": float("nan"), "rainfall": float("nan")})
    return out


if __name__ == "__main__":
    new = fetch()
    if RAW_PATH.exists():
        new = pd.concat([pd.read_csv(RAW_PATH, parse_dates=["date"]), new])
    new = new.drop_duplicates(["date", "market", "crop"])
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    new.to_csv(RAW_PATH, index=False)
    print(f"{len(new)} rows in {RAW_PATH}")
