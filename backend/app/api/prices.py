from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import config, schemas
from ..database import get_db
from ..models import Market
from ..services import price_service

router = APIRouter(tags=["prices"])


@router.get("/markets", response_model=list[schemas.MarketOut])
def markets(db: Session = Depends(get_db)):
    return db.query(Market).order_by(Market.name).all()


@router.get("/prices/predict", response_model=schemas.PricePredictionOut)
def predict(crop: str, market: str, db: Session = Depends(get_db)):
    m = db.query(Market).filter(Market.name.ilike(market)).first()
    if not m:
        raise HTTPException(404, "Unknown market")
    res = price_service.predict(db, crop.strip().lower(), m.id)
    if not res:
        raise HTTPException(404, "Not enough price history for this crop and market")
    return schemas.PricePredictionOut(crop=crop.lower(), market=m.name, horizon_days=config.PREDICTION_HORIZON_DAYS,
                                      predicted_price=res["price"], low=res["low"], high=res["high"], demand_index=res["demand_index"],
                                      volatility=res["volatility"], source=res["source"])


@router.get("/msp")
def msp():
    """Minimum Support Prices (Rs/quintal) used to flag buyers offering below MSP."""
    return config.MSP
