"""Import a CSV downloaded manually from the Agmarknet website (Price & Arrivals report) into our schema.
Column names are matched loosely (case-insensitive, substring), so small header differences are fine.
    python -m ml.data_ingestion.import_csv path/to/agmarknet_export.csv --out ml/data/raw_agmarknet.csv
Arrivals in tonnes are converted to quintals (x10)."""
import argparse
from pathlib import Path

import pandas as pd

from .fetch_agmarknet import COMMODITY_MAP

ALIASES = {
    "date": ["reported date", "arrival date", "price date", "date"],
    "market": ["market name", "market"],
    "commodity": ["commodity", "crop"],
    "min_price": ["min price", "minimum price", "min_price"],
    "max_price": ["max price", "maximum price", "max_price"],
    "modal_price": ["modal price", "modal_price"],
    "arrivals": ["arrivals", "arrival (tonnes)", "arrivals (tonnes)"],
}


def _find(cols, names):
    low = {c.lower().strip(): c for c in cols}
    for n in names:
        for lc, orig in low.items():
            if n in lc:
                return orig
    return None


def import_frame(raw: pd.DataFrame) -> pd.DataFrame:
    cols = {k: _find(raw.columns, v) for k, v in ALIASES.items()}
    missing = [k for k in ("date", "market", "commodity", "modal_price") if not cols[k]]
    if missing:
        raise ValueError(f"CSV is missing columns for: {missing}. Found: {list(raw.columns)}")
    out = pd.DataFrame({
        "date": pd.to_datetime(raw[cols["date"]], dayfirst=True, errors="coerce"),
        "market": raw[cols["market"]].astype(str).str.strip().str.title(),
        "crop": raw[cols["commodity"]].astype(str).str.strip().str.lower().map(
            lambda c: COMMODITY_MAP.get(c, c if c in COMMODITY_MAP.values() else None)),
        "modal_price": pd.to_numeric(raw[cols["modal_price"]], errors="coerce"),
    })
    out["min_price"] = pd.to_numeric(raw[cols["min_price"]], errors="coerce") if cols["min_price"] else out["modal_price"] * 0.95
    out["max_price"] = pd.to_numeric(raw[cols["max_price"]], errors="coerce") if cols["max_price"] else out["modal_price"] * 1.05
    out["arrivals"] = pd.to_numeric(raw[cols["arrivals"]], errors="coerce") * 10 if cols["arrivals"] else float("nan")
    out["rainfall"] = float("nan")
    return out.dropna(subset=["date", "crop", "modal_price"])[
        ["date", "market", "crop", "min_price", "max_price", "modal_price", "arrivals", "rainfall"]]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", type=Path)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "raw_agmarknet.csv")
    a = ap.parse_args()
    new = import_frame(pd.read_csv(a.csv))
    if a.out.exists():
        new = pd.concat([pd.read_csv(a.out, parse_dates=["date"]), new])
    new = new.drop_duplicates(["date", "market", "crop"]).sort_values(["market", "crop", "date"])
    a.out.parent.mkdir(parents=True, exist_ok=True)
    new.to_csv(a.out, index=False)
    print(f"{len(new):,} rows in {a.out}")
