"""Compare the ensemble with classical baselines on the same time-based split (7-day horizon):
naive (last price), seasonal naive (same date last year), Holt-Winters (statsmodels).
Prophet / LSTM are intentionally optional: add them as one more row if you install the packages.
    python -m ml.experiments.benchmarks"""
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from .._train_common import load_data
from ..metrics import mae, mape


def holt_winters_forecast(series: np.ndarray, horizon: int) -> float:
    try:
        fit = ExponentialSmoothing(series, trend="add", damped_trend=True).fit()
        return float(fit.forecast(horizon)[-1])
    except Exception:
        return float(series[-1])


def main(horizon: int = 7, sample_every: int = 15, window: int = 120):
    raw = load_data()
    rows = []
    for (m, c), g in raw.groupby(["market", "crop"]):
        p = g.sort_values("date")["modal_price"].values
        start = int(len(p) * 0.8)
        for t in range(start, len(p) - horizon, sample_every):
            rows.append({"actual": p[t + horizon], "naive": p[t], "seasonal_naive": p[t + horizon - 365] if t + horizon - 365 >= 0 else p[t],
                         "holt_winters": holt_winters_forecast(p[max(0, t - window):t + 1], horizon)})
    df = pd.DataFrame(rows)
    print(f"{len(df)} forecasts, horizon {horizon} days")
    for col in ("naive", "seasonal_naive", "holt_winters"):
        print(f"{col:16s} MAE={mae(df['actual'].values, df[col].values):.1f}  MAPE={mape(df['actual'].values, df[col].values):.2f}%")
    print("Ensemble numbers: see ml/models/price_h7_metrics.json")


if __name__ == "__main__":
    main()
