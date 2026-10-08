"""Train the demand-index model (0..1).  Run from repo root:  python -m ml.train_demand"""
import joblib

from ._train_common import MODELS_DIR, load_data, save_metrics
from .ensemble import Ensemble
from .features import FEATURE_COLS, build_training_set, time_split
from .metrics import mae, rmse

HORIZON = 7


def main():
    data, enc = build_training_set(load_data(), HORIZON)
    train, test = time_split(data)
    model = Ensemble().fit(train[FEATURE_COLS], train["target_demand"])
    y = test["target_demand"].values
    report = {"naive_current_index": {"MAE": mae(y, test["demand_index"].values), "RMSE": rmse(y, test["demand_index"].values)},
              "ensemble": {"MAE": mae(y, model.predict(test[FEATURE_COLS])), "RMSE": rmse(y, model.predict(test[FEATURE_COLS]))}}
    for k, v in report.items():
        print(f"{k:22s} MAE={v['MAE']:.4f} RMSE={v['RMSE']:.4f}")
    final = Ensemble().fit(data[FEATURE_COLS], data["target_demand"])
    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump({"model": final, "encoders": enc, "features": FEATURE_COLS, "horizon": HORIZON,
                 "metrics": report}, MODELS_DIR / "demand_ensemble.joblib")
    save_metrics("demand", report)
    print("saved ml/models/demand_ensemble.joblib")


if __name__ == "__main__":
    main()
