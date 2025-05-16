from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from . import models, schemas
from fastapi import Header, HTTPException, Depends
from .database import get_db

# TODO:Тут в crud..balances такая же функция, проверить выдает ли ошибку
async def get_user_balances(db: AsyncSession, user_id: str):
    # TODO: поправить тикер, т.к. выдает 500 ошибку
    result = await db.execute(
        select(models.Balance.instrument_ticker, models.Balance.amount)
        .where(models.Balance.user_id == user_id)
    )
    return result.all()

# TODO: у нас есть дублирование этого в admin.py
async def withdraw_balance(db: AsyncSession, user_id: str, ticker: str, amount: int):
    result = await db.execute(
        select(models.Balance).where(
            models.Balance.user_id == user_id,
            models.Balance.ticker == ticker
        )
    )
    balance = result.scalar_one_or_none()
    
    if not balance:
        raise ValueError("Balance not found")
    
    if balance.amount < amount:
        raise ValueError("Insufficient funds")
    
    balance.amount -= amount
    await db.commit()
    return balance

# TODO: перенести в crud..orderbook?
async def get_orderbook_data(db: AsyncSession, ticker: str, limit: int = 10):
    instrument = await db.execute(
        select(models.Instrument).where(models.Instrument.ticker == ticker)
        #TODO: тут ошибка
    )
    if not instrument.scalar_one_or_none():
        raise ValueError(f"Инструмент {ticker} не найден")

    bids_result = await db.execute(
        select(models.Order)
        .where(
            models.Order.ticker == ticker,
            models.Order.direction == "BUY",
            models.Order.status == "NEW"
        )
        .order_by(models.Order.price.desc())
        .limit(limit)
    )
    bids = [{"price": o.price, "qty": o.qty} for o in bids_result.scalars().all()]

    asks_result = await db.execute(
        select(models.Order)
        .where(
            models.Order.ticker == ticker,
            models.Order.direction == "SELL",
            models.Order.status == "NEW"
        )
        .order_by(models.Order.price.asc())
        .limit(limit)
    )
    asks = [{"price": o.price, "qty": o.qty} for o in asks_result.scalars().all()]

    if not bids and not asks:
        return None

    return {
        "bids": bids,
        "asks": asks
    }

