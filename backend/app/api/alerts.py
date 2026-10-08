from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..models import Market, Notification, PriceAlert, User
from ..security import get_current_user

router = APIRouter(tags=["alerts"])


@router.post("/alerts", response_model=schemas.AlertOut, status_code=201)
def create_alert(body: schemas.AlertCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    market_id = None
    if body.market:
        m = db.query(Market).filter(Market.name.ilike(body.market)).first()
        if not m:
            raise HTTPException(404, "Unknown market")
        market_id = m.id
    a = PriceAlert(user_id=user.id, crop=body.crop, market_id=market_id, threshold_pct=body.threshold_pct)
    db.add(a)
    db.commit()
    return a


@router.get("/alerts", response_model=list[schemas.AlertOut])
def my_alerts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(PriceAlert).filter(PriceAlert.user_id == user.id).all()


@router.delete("/alerts/{alert_id}", status_code=204)
def delete_alert(alert_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.get(PriceAlert, alert_id)
    if not a or a.user_id != user.id:
        raise HTTPException(404, "Alert not found")
    db.delete(a)
    db.commit()


@router.get("/notifications", response_model=list[schemas.NotificationOut])
def notifications(unread: bool = False, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Notification).filter(Notification.user_id == user.id)
    if unread:
        q = q.filter(Notification.read.is_(False))
    return q.order_by(Notification.id.desc()).limit(50).all()


@router.post("/notifications/read-all")
def read_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(Notification).filter(Notification.user_id == user.id, Notification.read.is_(False)).update({"read": True})
    db.commit()
    return {"marked": n}


@router.patch("/me/language")
def set_language(lang: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if lang not in ("en", "te"):
        raise HTTPException(400, "Supported languages: en, te")
    user.language = lang
    db.commit()
    return {"language": lang}
