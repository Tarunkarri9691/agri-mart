"""Daily rainfall per market from Open-Meteo (free, no API key).  https://open-meteo.com
    python -m ml.data_ingestion.fetch_weather --start 2024-01-01 --end 2026-10-01 --out ml/data/weather.csv"""
import argparse
from pathlib import Path

import pandas as pd
import requests

from .markets import MARKETS

URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_market(lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    r = requests.get(URL, params={"latitude": lat, "longitude": lon, "start_date": start, "end_date": end,
                                  "daily": "precipitation_sum", "timezone": "Asia/Kolkata"}, timeout=60)
    r.raise_for_status()
    d = r.json()["daily"]
    return pd.DataFrame({"date": pd.to_datetime(d["time"]), "rainfall": d["precipitation_sum"]})


def fetch_all(start: str, end: str) -> pd.DataFrame:
    frames = []
    for name, _, lat, lon in MARKETS:
        f = fetch_market(lat, lon, start, end)
        f["market"] = name
        frames.append(f)
    return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "weather.csv")
    a = ap.parse_args()
    df = fetch_all(a.start, a.end)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.out, index=False)
    print(f"{len(df):,} rows -> {a.out}")
