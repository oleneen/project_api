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

def execute_trade(db: Session, buy_order: models.Order, sell_order: models.Order, 
                 qty: int, ticker: str):
    # Обновляем балансы
    # Покупатель получает акции, теряет деньги
    update_balance(db, buy_order.user_id, ticker, qty)
    update_balance(db, buy_order.user_id, "RUB", -qty * sell_order.price)
    
    # Продавец получает деньги, теряет акции
    update_balance(db, sell_order.user_id, ticker, -qty)
    update_balance(db, sell_order.user_id, "RUB", qty * sell_order.price)
    
    # Создаем запись о сделке
    trade = models.Trade(
        buy_order_id=buy_order.id,
        sell_order_id=sell_order.id,
        ticker=ticker,
        qty=qty,
        price=sell_order.price,
        executed_at=datetime.now()
    )
    db.add(trade)

def update_balance(db: Session, user_id: str, ticker: str, amount: int):
    balance = db.query(models.Balance).filter(
        models.Balance.user_id == user_id,
        models.Balance.ticker == ticker
    ).first()
    
    if balance:
        balance.amount += amount
    else:
        balance = models.Balance(
            user_id=user_id,
            ticker=ticker,
            amount=amount
        )
        db.add(balance)
    
    if balance.amount < 0:
        raise ValueError("Negative balance not allowed")