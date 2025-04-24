from sqlalchemy.orm import Session
from . import models, schemas
from datetime import datetime

def get_user_by_token(db: Session, token: str):
    return db.query(models.User).filter(models.User.api_key == token).first()

def create_order(db: Session, user_id: str, order_data):
    # Здесь должна быть логика создания ордера
    pass

def get_user_balances(db: Session, user_id: str):
    # Логика получения балансов
    pass

def create_instrument(db: Session, instrument: schemas.Instrument):
    db_instrument = models.Instrument(**instrument.dict())
    db.add(db_instrument)
    db.commit()
    db.refresh(db_instrument)
    return db_instrument

def get_instruments(db: Session):
    return db.query(models.Instrument).all()

def create_user_balance(db: Session, user_id: str, ticker: str, amount: int):
    balance = models.Balance(user_id=user_id, ticker=ticker, amount=amount)
    db.add(balance)
    db.commit()
    return balance

def get_user_balances(db: Session, user_id: str):
    return db.query(models.Balance).filter(models.Balance.user_id == user_id).all()

def create_order(db: Session, order: schemas.LimitOrderBody | schemas.MarketOrderBody, user_id: str):
    db_order = models.Order(
        user_id=user_id,
        **order.dict()
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

<<<<<<< HEAD
def get_order_by_id(db: Session, order_id: str, user_id: str = None):
    query = db.query(models.Order).filter(models.Order.id == order_id)
    #проверяем принадлежит ли ордер пользователю - опционально, можно не проверять
    if user_id:
        query = query.filter(models.Order.user_id == user_id)
    return query.first()
=======

def withdraw_balance(db: Session, user_id: str, ticker: str, amount: int):
    balance = db.query(models.Balance).filter(
        models.Balance.user_id == user_id,
        models.Balance.ticker == ticker
    ).first()

    if not balance:
        raise ValueError("Balance not found")

    if balance.amount < amount:
        raise ValueError("Insufficient funds")

    balance.amount -= amount
    db.commit()
    return balance
>>>>>>> f2bd57f5aa4260504f989634c522b81857941e6d
