"""Train multi-horizon price models with conformal prediction intervals.
Run from repo root:   python -m ml.train_price                 (all horizons: 3, 7, 14)
                      python -m ml.train_price --horizons 7    (single horizon)"""
import argparse

import joblib
import numpy as np

from ._train_common import HORIZONS, INTERVAL_ALPHA, MODELS_DIR, load_data, save_metrics
from .conformal import fit_conformal, offsets_for
from .ensemble import Ensemble
from .features import FEATURE_COLS, build_training_set, time_split
from .metrics import mae, mape, rmse


def train_horizon(raw, horizon: int):
    data, enc = build_training_set(raw, horizon)
    train, test = time_split(data)
    proper, cal = time_split(train, test_frac=0.15)
    print(f"[h={horizon}] train={len(proper):,} calibration={len(cal):,} test={len(test):,} (time-based splits)")

    model = Ensemble().fit(proper[FEATURE_COLS], proper["target_return"])
    resid = cal["target_return"].values - model.predict(cal[FEATURE_COLS])
    conf = fit_conformal(cal["crop"].values, resid, INTERVAL_ALPHA)

    y, cur = test["target_price"].values, test["modal_price"].values
    report = {"naive_last_price": {"MAE": mae(y, cur), "RMSE": rmse(y, cur), "MAPE": mape(y, cur)}}
    for name, r in model.predict_members(test[FEATURE_COLS]).items():
        p = cur * (1 + r)
        report[name] = {"MAE": mae(y, p), "RMSE": rmse(y, p), "MAPE": mape(y, p)}
    pred_ret = model.predict(test[FEATURE_COLS])
    p = cur * (1 + pred_ret)
    report["ensemble"] = {"MAE": mae(y, p), "RMSE": rmse(y, p), "MAPE": mape(y, p)}
    offs = np.array([offsets_for(conf, c) for c in test["crop"]])
    lo, hi = cur * (1 + pred_ret + offs[:, 0]), cur * (1 + pred_ret + offs[:, 1])
    cover = float(np.mean((y >= lo) & (y <= hi)))
    report["interval"] = {"nominal_coverage": 1 - INTERVAL_ALPHA, "empirical_coverage": cover,
                          "mean_width_pct": float(np.mean((hi - lo) / cur) * 100)}
    for k, v in report.items():
        if k == "interval":
            print(f"  interval coverage={v['empirical_coverage']:.2%} (target {v['nominal_coverage']:.0%}) width={v['mean_width_pct']:.1f}%")
        else:
            print(f"  {k:18s} MAE={v['MAE']:.1f} RMSE={v['RMSE']:.1f} MAPE={v['MAPE']:.2f}%")

    final = Ensemble().fit(data[FEATURE_COLS], data["target_return"])
    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump({"model": final, "encoders": enc, "features": FEATURE_COLS, "horizon": horizon, "target": "return",
                 "conformal": conf, "metrics": report}, MODELS_DIR / f"price_h{horizon}.joblib")
    save_metrics(f"price_h{horizon}", report)
    print(f"  saved ml/models/price_h{horizon}.joblib")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizons", type=int, nargs="+", default=list(HORIZONS))
    args = ap.parse_args()
    raw = load_data()
    for h in args.horizons:
        train_horizon(raw, h)


if __name__ == "__main__":
    main()
