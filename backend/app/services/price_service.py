"""Price & demand signal for a (crop, market): ML ensemble with conformal interval when trained,
otherwise a statistical fallback (patent step 230 / ref 150)."""
import logging
import math

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from .. import config
from ..models import Market, MarketPrice, Prediction

log = logging.getLogger(__name__)


def history_df(db: Session, crop: str, market: Market, days: int = 150) -> pd.DataFrame:
    rows = (db.query(MarketPrice).filter(MarketPrice.crop == crop, MarketPrice.market_id == market.id)
            .order_by(MarketPrice.date.desc()).limit(days).all())
    df = pd.DataFrame([{"date": r.date, "market": market.name, "crop": crop, "min_price": r.min_price,
                        "max_price": r.max_price, "modal_price": r.modal_price,
                        "arrivals": r.arrivals, "rainfall": r.rainfall} for r in rows])
    return df.sort_values("date").reset_index(drop=True) if len(df) else df


def _fallback(df: pd.DataFrame) -> tuple[float, float]:
    price = float(df["modal_price"].tail(7).mean())
    a7, a30 = df["arrivals"].tail(7).mean(), df["arrivals"].tail(30).mean()
    arr_ratio = a7 / a30 if a30 else 1.0
    mom = df["modal_price"].tail(7).mean() / df["modal_price"].tail(30).mean()
    demand = float(np.clip(0.5 + (mom - 1) * 2.5 - (arr_ratio - 1), 0, 1))  # same formula as ml/features.py
    return price, demand


def latest_price(db: Session, crop: str, market_id: int) -> float | None:
    row = (db.query(MarketPrice).filter(MarketPrice.crop == crop, MarketPrice.market_id == market_id)
           .order_by(MarketPrice.date.desc()).first())
    return float(row.modal_price) if row else None


def predict(db: Session, crop: str, market_id: int, persist: bool = True, horizon: int = config.PREDICTION_HORIZON_DAYS,
            explain: bool = True) -> dict | None:
    market = db.get(Market, market_id)
    df = history_df(db, crop, market) if market else pd.DataFrame()
    if len(df) < 5:
        return None
    recent = df["modal_price"].tail(30)
    volatility = float(recent.std() / recent.mean()) if len(recent) > 1 else 0.1
    price = low = high = demand = None
    source, drivers = "statistical_fallback", []
    if len(df) >= 35:
        try:
            from ml.predict import predict_price
            out = predict_price(df, crop, market.name, horizon=horizon, explain=explain)
            price, low, high, demand = out["price"], out["low"], out["high"], out["demand_index"]
            source, drivers = "ml_ensemble", out["drivers"]
        except Exception as exc:  # model not trained / unseen crop-market
            log.info("ML prediction unavailable (%s); using fallback", exc)
    if price is None:
        price, demand = _fallback(df)
        half = 1.28 * volatility * 0.5 * math.sqrt(horizon / 7)   # heuristic 80% band when no trained model
        low, high = price * (1 - half), price * (1 + half)
    uncertainty = (high - low) / (2 * price) if price else 0.0     # relative half-width of the interval
    result = {"price": round(float(price), 2), "low": round(float(low), 2), "high": round(float(high), 2),
              "demand_index": round(float(demand), 3), "volatility": round(volatility, 4),
              "uncertainty": round(float(uncertainty), 4), "source": source, "drivers": drivers,
              "market": market.name, "market_id": market.id, "horizon": horizon}
    if persist:
        db.add(Prediction(crop=crop, market_id=market.id, horizon_days=horizon, predicted_price=result["price"],
                          demand_index=result["demand_index"], source=source))
        db.commit()
    return result
