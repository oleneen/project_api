from sqlalchemy import select,and_
from sqlalchemy.ext.asyncio import AsyncSession
from .. import models, schemas
from ..crud.instruments import get_instrument_by_ticker
from ..crud.balances import get_user_balance, lock_user_balance, ensure_and_lock_balance
import logging
from ..schemas import OrderStatus
from ..models import Order,OrderDirection
from ..matching import execute_limit_order,execute_market_order

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

async def process_market_order(db: AsyncSession, order_data: schemas.MarketOrderBody, user_id: str):
    try:
        instrument = await get_instrument_by_ticker(db, order_data.ticker)
        if not instrument:
            raise ValueError(f"Инструмент {order_data.ticker} не найден")

        opposite_side = OrderDirection.SELL if order_data.direction == "BUY" else OrderDirection.BUY
        db_order = models.Order(
            user_id=user_id,
            direction=order_data.direction,
            instrument_ticker=order_data.ticker,
            qty=order_data.qty,
            price=None,
            type="MARKET",
            status=OrderStatus.NEW,
            filled=0
        )
        db.add(db_order)
        await db.commit()  
        await db.refresh(db_order)

        stmt = (
            select(Order)
            .where(
                and_(
                    Order.instrument_ticker == order_data.ticker,
                    Order.direction == opposite_side,
                    Order.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
                    Order.type == "LIMIT"
                )
            )
            .order_by(Order.price.asc() if order_data.direction == "BUY" else Order.price.desc(), Order.timestamp)
        )
        result = await db.execute(stmt)
        matching_orders = result.scalars().all()
        if not matching_orders:
            db_order.status = OrderStatus.CANCELLED  # или просто "CANCELED" если без Enum
            await db.commit()
            raise ValueError("Нет подходящих лимитных ордеров для исполнения рыночной заявки")

        # Новая проверка: суммарное доступное количество лимитных ордеров
        total_available_qty = sum(o.qty - o.filled for o in matching_orders)
        if total_available_qty < order_data.qty:
            db_order.status = OrderStatus.CANCELLED  # или просто "CANCELED" если без Enum
            await db.commit()
            raise ValueError(f"Недостаточно встречных лимитных ордеров: доступно {total_available_qty}, требуется {order_data.qty}")

        balance_ticker = "RUB" if order_data.direction == "BUY" else order_data.ticker
        balance = await get_user_balance(db, user_id, balance_ticker)

        max_price = max(o.price for o in matching_orders) if order_data.direction == "BUY" else 0
        required_amount = order_data.qty * max_price if order_data.direction == "BUY" else order_data.qty
        if balance < required_amount:
            db_order.status = OrderStatus.CANCELLED  # или просто "CANCELED" если без Enum
            await db.commit()
            raise ValueError(f"Недостаточно {balance_ticker} (требуется примерно {required_amount}, доступно {balance})")
        
        await lock_user_balance(db, user_id, balance_ticker, required_amount)
    
        await execute_market_order(db, db_order)
        await db.commit()  
        return db_order

    except Exception as e:
        await db.rollback()
        await db.commit()
        raise ValueError(f"Ошибка исполнения рыночного ордера: {str(e)}")


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

        bal = await ensure_and_lock_balance(db, user_id, balance_ticker, required_amount)
        await db.refresh(bal)

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

        db.add(db_order)
        await db.flush()
        await execute_limit_order(db, db_order)
        await db.commit()
        await db.refresh(db_order)
        return db_order

    except Exception as e:
        await db.rollback()
        raise ValueError(f"Ошибка при создании лимитного ордера: {str(e)}")