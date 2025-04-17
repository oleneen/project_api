from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from .. import schemas, models, crud
from ..database import get_db
from typing import Optional
import uuid

router = APIRouter(prefix="/api/v1")

# Пример защиты эндпоинта
def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)):
    if not authorization.startswith("TOKEN "):
        raise HTTPException(status_code=401, detail="Invalid token format")
    token = authorization[6:]
    user = crud.get_user_by_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

@router.get("/balance")
def get_balances(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение балансов пользователя"""
    return crud.get_user_balances(db, current_user.id)

@router.post("/order")
def create_order(
    order_data: schemas.LimitOrderBody | schemas.MarketOrderBody,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создание новой заявки"""
    return crud.create_order(db, current_user.id, order_data)

@router.get("/order")
def list_orders(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Список активных заявок пользователя"""
    return crud.get_user_orders(db, current_user.id)

@router.delete("/order/{order_id}")
def cancel_order(order_id: str, current_user: models.User = Depends(get_current_user), 
                 db: Session = Depends(get_db)):
    return crud.cancel_order(db, order_id, current_user.id)

@router.get("/order/{order_id}")
def get_order(order_id: str, current_user: models.User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    return crud.get_order(db, order_id, current_user.id)

@router.get("/trades")
def get_trade_history(ticker: str, current_user: models.User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    return crud.get_trade_history(db, ticker, current_user.id)