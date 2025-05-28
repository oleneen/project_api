from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .. import models, schemas
from ..crud.instruments import get_instrument_by_ticker
from ..crud.balances import update_user_balance,get_user_balance, get_available_balance, lock_user_balance
import logging
from ..matching import execute_limit_order

logger = logging.getLogger(__name__) 

async def get_order_by_id(db: AsyncSession, order_id: str, user_id: str = None):
    stmt = select(models.Order).where(models.Order.id == order_id)
    if user_id:
        stmt = stmt.where(models.Order.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_orders_by_user_id(db: AsyncSession, user_id: str):
    result = await db.execute(
        select(models.Order).where(models.Order.user_id == str(user_id))
    )
    return result.scalars().all()

async def process_market_order(
    db: AsyncSession, 
    order_data: schemas.MarketOrderBody, 
    user_id: str
):
    try:
        instrument = await get_instrument_by_ticker(db, order_data.ticker)
        if not instrument:
            raise ValueError(f"Инструмент {order_data.ticker} не найден")

        balance_ticker = "RUB" if order_data.direction == "BUY" else order_data.ticker
        required_amount = order_data.qty
        
        balance = await get_user_balance(db, user_id, balance_ticker)
        if balance < required_amount:
            error_msg = (f"Недостаточно {balance_ticker} "
                        f"(требуется: {required_amount}, доступно: {balance})")
            raise ValueError(error_msg)

        db_order = models.Order(
            user_id=user_id,
            direction=order_data.direction,
            instrument_ticker=order_data.ticker,
            qty=order_data.qty,
            price=None,
            type="MARKET",
            status="NEW",
            filled=0
        )
        
        db.add(db_order)
        await db.commit()
        await db.refresh(db_order)
        return db_order

    except Exception as e:
        await db.rollback()
        raise ValueError(f"Ошибка при создании рыночного ордера: {str(e)}")

async def process_limit_order(
    db: AsyncSession,
    order_data: schemas.LimitOrderBody,
    user_id: str
):
    try:
        instrument = await get_instrument_by_ticker(db, order_data.ticker)
        if not instrument:
            raise ValueError(f"Инструмент {order_data.ticker} не найден")

        balance_ticker = "RUB" if order_data.direction == "BUY" else order_data.ticker
        required_amount = order_data.price * order_data.qty if order_data.direction == "BUY" else order_data.qty

        balance = await get_available_balance(db, user_id, balance_ticker)
        if balance < required_amount:
            error_msg = (f"Недостаточно {balance_ticker} "
                        f"(требуется: {required_amount}, доступно: {balance})")
            raise ValueError(error_msg)

        db_order = models.Order(
            user_id=user_id,
            direction=order_data.direction,
            instrument_ticker=order_data.ticker,
            qty=order_data.qty,
            price=order_data.price,
            type="LIMIT",
            status="NEW",
            filled=0
        )
        
        await lock_user_balance(db, user_id, balance_ticker, required_amount)

        db.add(db_order)
        await db.commit()
        await db.refresh(db_order)
        await execute_limit_order(db, db_order)
        return db_order

    except Exception as e:
        await db.rollback()
        raise ValueError(f"Ошибка при создании лимитного ордера: {str(e)}")