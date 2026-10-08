import json
from pathlib import Path

import pandas as pd

from .data_ingestion.generate_synthetic import DATA_PATH, generate

MODELS_DIR = Path(__file__).resolve().parent / "models"


def load_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        print("No data found - generating synthetic data (use fetch_agmarknet + clean for real data).")
        generate()
    return pd.read_csv(DATA_PATH, parse_dates=["date"])


def save_metrics(name: str, metrics: dict):
    MODELS_DIR.mkdir(exist_ok=True)
    (MODELS_DIR / f"{name}_metrics.json").write_text(json.dumps(metrics, indent=2))

HORIZONS = (3, 7, 14)      # days ahead (multi-horizon forecasts, enables "sell now vs wait")
DEFAULT_HORIZON = 7
INTERVAL_ALPHA = 0.2       # 80% prediction intervals
