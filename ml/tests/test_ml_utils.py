import numpy as np
import pandas as pd

from ml.conformal import fit_conformal, interval_offsets, offsets_for
from ml.data_ingestion.build_dataset import merge
from ml.data_ingestion.import_csv import import_frame
from ml.features import add_features


def test_conformal_interval_covers_nominal():
    rng = np.random.default_rng(0)
    cal, test = rng.normal(0, 0.03, 5000), rng.normal(0, 0.03, 5000)
    lo, hi = interval_offsets(cal, 0.2)
    assert 0.77 < np.mean((test >= lo) & (test <= hi)) < 0.83
    conf = fit_conformal(np.array(["a"] * 2500 + ["b"] * 2500), np.concatenate([rng.normal(0, 0.01, 2500), rng.normal(0, 0.05, 2500)]))
    assert offsets_for(conf, "b")[1] > offsets_for(conf, "a")[1] * 3       # volatile crop -> wider band
    assert offsets_for(conf, "unknown") == conf["global"]


def test_import_agmarknet_export_with_loose_headers():
    raw = pd.DataFrame({"Reported Date": ["01-Oct-2026", "02-Oct-2026"], "Market Name": ["eluru", "eluru"],
                        "Commodity": ["Maize", "Maize"], "Min Price (Rs./Quintal)": [2000, 2050],
                        "Max Price (Rs./Quintal)": [2200, 2250], "Modal Price (Rs./Quintal)": [2100, 2150],
                        "Arrivals (Tonnes)": [12.5, 10.0]})
    out = import_frame(raw)
    assert list(out["crop"]) == ["maize", "maize"] and out["market"].iloc[0] == "Eluru"
    assert out["arrivals"].iloc[0] == 125.0                                 # tonnes -> quintals


def test_merge_adds_weather_and_arrivals_and_cleans():
    dates = pd.date_range("2026-01-01", periods=40)
    prices = pd.DataFrame({"date": dates, "market": "Eluru", "crop": "paddy", "min_price": 2000.0, "max_price": 2200.0,
                           "modal_price": 2100.0, "arrivals": np.nan, "rainfall": np.nan})
    weather = pd.DataFrame({"date": dates, "market": "eluru", "rainfall": 3.0})
    arrivals = pd.DataFrame({"date": dates, "market": "Eluru", "crop": "paddy", "arrivals": 250.0})
    out = merge(prices, weather, arrivals)
    assert len(out) == 40 and (out["rainfall"] == 3.0).all() and (out["arrivals"] == 250.0).all()


def test_demand_index_formula_matches_backend_fallback():
    dates = pd.date_range("2026-01-01", periods=60)
    df = pd.DataFrame({"date": dates, "market": "Eluru", "crop": "paddy", "min_price": 1900.0, "max_price": 2300.0,
                       "modal_price": np.linspace(2000, 2300, 60), "arrivals": np.linspace(300, 200, 60), "rainfall": 0.0})
    f = add_features(df).iloc[-1]
    mom = df["modal_price"].tail(7).mean() / df["modal_price"].tail(30).mean()
    arr = df["arrivals"].tail(7).mean() / df["arrivals"].tail(30).mean()
    expected = float(np.clip(0.5 + (mom - 1) * 2.5 - (arr - 1), 0, 1))
    assert abs(f["demand_index"] - expected) < 1e-9
