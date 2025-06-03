from . import models
from sqlalchemy import and_, select
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from .crud.balances import transfer_balance
from .crud.transactions import create_transaction
from .models import Order, OrderDirection, OrderStatus,OrderType

logger = logging.getLogger(__name__)

async def execute_limit_order(session: AsyncSession, order: Order) -> None:
    opposite_side = OrderDirection.SELL if order.direction == OrderDirection.BUY else OrderDirection.BUY

    stmt = (
        select(Order)
        .where(
            and_(
                Order.instrument_ticker == order.instrument_ticker,
                Order.direction == opposite_side,
                Order.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
                Order.price <= order.price if order.direction == OrderDirection.BUY else Order.price >= order.price,
            )
        )
        .order_by(Order.timestamp)
    )

    result = await session.execute(stmt)
    matching_orders = result.scalars().all()

    if not matching_orders:
        return

    remaining_qty = order.qty - order.filled

    for counter_order in matching_orders:
        if remaining_qty == 0:
            break

        available_qty = counter_order.qty - counter_order.filled
        trade_qty = min(remaining_qty, available_qty)
        trade_price = counter_order.price

        buyer_id = order.user_id if order.direction == OrderDirection.BUY else counter_order.user_id
        seller_id = counter_order.user_id if order.direction == OrderDirection.BUY else order.user_id

        await transfer_balance(session, buyer_id, seller_id, trade_qty * trade_price)
        await execute_trade(session, order, counter_order, trade_qty, trade_price)

        counter_order.filled += trade_qty
        if counter_order.filled == counter_order.qty:
            counter_order.status = OrderStatus.EXECUTED
        else:
            counter_order.status = OrderStatus.PARTIALLY_EXECUTED

        remaining_qty -= trade_qty

    order.filled = order.qty - remaining_qty
    if order.filled == order.qty:
        order.status = OrderStatus.EXECUTED
    else:
        order.status = OrderStatus.PARTIALLY_EXECUTED

    await session.commit()

async def execute_market_order(session: AsyncSession, order: Order) -> None:
    opposite_side = OrderDirection.SELL if order.direction == OrderDirection.BUY else OrderDirection.BUY

    stmt = (
        select(Order)
        .where(
            and_(
                Order.instrument_ticker == order.instrument_ticker,
                Order.direction == opposite_side,
                Order.status == OrderStatus.NEW,
                Order.price.isnot(None), 
                Order.type == OrderType.LIMIT  
            )
        )
        .order_by(
            Order.price.asc() if order.direction == OrderDirection.BUY else Order.price.desc(),
            Order.timestamp.asc()
        )
    )

    result = await session.execute(stmt)
    matching_orders = result.scalars().all()

    if not matching_orders:
        return

    remaining_qty = order.qty - order.filled

    for counter_order in matching_orders:
        if remaining_qty == 0:
            break

        available_qty = counter_order.qty - counter_order.filled
        trade_qty = min(remaining_qty, available_qty)
        trade_price = counter_order.price

        if order.direction == OrderDirection.BUY:
            buyer_id = order.user_id
            seller_id = counter_order.user_id
        else:
            buyer_id = counter_order.user_id
            seller_id = order.user_id

        await transfer_balance(session, buyer_id, seller_id, trade_qty * trade_price)
        await execute_trade(session, order, counter_order, trade_qty, trade_price)

        counter_order.filled += trade_qty
        if counter_order.filled == counter_order.qty:
            counter_order.status = OrderStatus.EXECUTED
        else:
            counter_order.status = OrderStatus.PARTIALLY_EXECUTED

        remaining_qty -= trade_qty

    order.filled = order.qty - remaining_qty
    if order.filled == order.qty:
        order.status = OrderStatus.EXECUTED
    else:
        order.status = OrderStatus.PARTIALLY_EXECUTED

    await session.commit()

async def execute_trade(
    session: AsyncSession,
    order1: models.Order,
    order2: models.Order,
    qty: float,
    price: float,
):
    try:
        buyer = order1 if order1.direction == OrderDirection.BUY else order2
        seller = order2 if order1.direction == OrderDirection.BUY else order1

        transaction = models.Transaction(
            ticker=order1.instrument_ticker,
            qty=qty,
            price=price,
            buy_order_id=buyer.id,
            sell_order_id=seller.id
        )
        session.add(transaction)

        await create_transaction(order1, order2, qty, session)  

    except Exception as e:
        await session.rollback()
        logger.error(f"Trade execution failed: {str(e)}")
        raise