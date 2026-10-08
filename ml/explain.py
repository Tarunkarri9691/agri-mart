"""Explainability (patent ref 350/450/550): SHAP drivers for a single prediction."""
import numpy as np

LABELS = {"price_lag_1": "yesterday's price", "price_lag_7": "price a week ago", "price_lag_14": "price two weeks ago",
          "price_roll_7": "7-day average price", "price_roll_30": "30-day average price", "modal_price": "current price",
          "momentum": "recent price momentum", "arr_ratio": "arrivals vs normal", "arrivals": "market arrivals",
          "rainfall": "rainfall", "rain_roll_7": "weekly rainfall", "month": "month of year", "doy_sin": "season",
          "doy_cos": "season", "demand_index": "current demand", "crop_code": "crop", "market_code": "market"}


_explainers: dict = {}


def top_drivers(model, X_row, k: int = 5) -> list[dict]:
    """X_row: single-row DataFrame. Impacts are converted to Rs/quintal (SHAP of the % change x current price)."""
    try:
        import shap
        if id(model) not in _explainers:  # building the explainer is the slow part - cache it
            _explainers[id(model)] = shap.TreeExplainer(model.xgb)
        sv = _explainers[id(model)].shap_values(X_row)[0]
    except Exception:  # shap missing -> fall back to XGBoost's own contribution values
        import xgboost as xgb
        sv = model.xgb.get_booster().predict(xgb.DMatrix(X_row), pred_contribs=True)[0][:-1]
    sv = np.asarray(sv) * float(X_row["modal_price"].iloc[0])
    order = np.argsort(-np.abs(sv))[:k]
    cols = list(X_row.columns)
    return [{"feature": cols[i], "label": LABELS.get(cols[i], cols[i]), "value": float(X_row.iloc[0, i]),
             "impact_rs": round(float(sv[i]), 2)} for i in order]
