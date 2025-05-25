from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .. import models, schemas
from .. import schemas, models, crud
from ..crud.instruments import get_instrument_by_ticker
from ..crud.balances import update_user_balance,get_user_balance, get_available_balance, lock_user_balance
import logging

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

async def create_order(db: AsyncSession, order: schemas.LimitOrderBody | schemas.MarketOrderBody, user_id: str):
    db_order = models.Order(
        user_id=user_id,
        **order.dict()
    )
    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)
    return db_order

async def process_market_order(
    db: AsyncSession,
    order: schemas.MarketOrderBody,
    user_id: str
):
    instrument = await get_instrument_by_ticker(db, order.ticker)
    if not instrument:
        raise ValueError(f"Инструмент {order.ticker} не найден")

    db_order = await create_order(db, order, user_id)
    remaining_qty = order.qty
    total_executed = 0
    avg_price = 0

    if order.direction == "BUY":
        opposite_direction = "SELL"
        order_by = models.Order.price.asc()
    else:
        opposite_direction = "BUY"
        order_by = models.Order.price.desc()

    while remaining_qty > 0:
        opposite_orders = await db.execute(
            select(models.Order)
            .where(
                models.Order.ticker == order.ticker,
                models.Order.direction == opposite_direction,
                models.Order.status == "NEW"
            )
            .order_by(order_by)
        )
        opposite_orders = opposite_orders.scalars().all()

        if not opposite_orders:
            break 

        for opposite_order in opposite_orders:
            if remaining_qty <= 0:
                break

            available_qty = opposite_order.qty - opposite_order.filled
            executed_qty = min(available_qty, remaining_qty)

            opposite_order.filled += executed_qty
            if opposite_order.filled >= opposite_order.qty:
                opposite_order.status = "FILLED"

            db_order.filled += executed_qty
            if db_order.filled >= db_order.qty:
                db_order.status = "FILLED"

            if order.direction == "BUY":
                await crud.update_user_balance(db, user_id, order.ticker, executed_qty)
                await update_user_balance(db, opposite_order.user_id, order.ticker, -executed_qty)
                await update_user_balance(db, user_id, "USD", -executed_qty * opposite_order.price)
                await update_user_balance(db, opposite_order.user_id, "USD", executed_qty * opposite_order.price)
            else:
                await update_user_balance(db, user_id, order.ticker, -executed_qty)
                await update_user_balance(db, opposite_order.user_id, order.ticker, executed_qty)
                await update_user_balance(db, user_id, "USD", executed_qty * opposite_order.price)
                await update_user_balance(db, opposite_order.user_id, "USD", -executed_qty * opposite_order.price)

            total_executed += executed_qty
            avg_price = (avg_price * (total_executed - executed_qty) + opposite_order.price * executed_qty) / total_executed
            remaining_qty -= executed_qty

        await db.commit()

    if db_order.filled > 0:
        if db_order.filled < db_order.qty:
            db_order.status = "PARTIALLY_FILLED"
        await db.commit()
        await db.refresh(db_order)

    return {
        "order": db_order,
        "executed_qty": total_executed,
        "avg_price": avg_price if total_executed > 0 else None
    }


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
        return db_order

    except Exception as e:
        await db.rollback()
        raise ValueError(f"Ошибка при создании лимитного ордера: {str(e)}")