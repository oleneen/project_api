from . import models
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from .crud.balances import apply_trade
from .crud.transactions import create_transaction
from .schemas import Direction
from .models import Order,  OrderStatus,OrderType,OrderDirection

async def execute_limit_order(session: AsyncSession, order: Order) -> None:
    print(f"Opposite side: {order.direction}")
    opposite_side = Direction.SELL if order.direction == Direction.BUY else Direction.BUY
    print(f"Opposite side: {order.direction}")
    print(f"Opposite side: {opposite_side}")
    stmt = (
        select(Order)
        .where(
            and_(
                Order.instrument_ticker == order.instrument_ticker,
                Order.direction == opposite_side,
                Order.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
                Order.price <= order.price if order.direction == Direction.BUY else Order.price >= order.price,
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

        if order.direction == Direction.BUY:
                buyer_id = order.user_id
                seller_id = counter_order.user_id
        else:
            buyer_id = counter_order.user_id
            seller_id = order.user_id

        initial_locked_price = order.price if order.direction == Direction.SELL else counter_order.price

        await apply_trade(
            session,
            buyer_id,
            seller_id,
            order.instrument_ticker,
            trade_price,
            trade_qty,
            initial_locked_price
        )

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

    await session.flush()


async def execute_market_order(session: AsyncSession, order: Order) -> None:
    try:
        print(f"Order: {order.type, order.direction}")
        opposite_side = OrderDirection.SELL if order.direction == OrderDirection.BUY else OrderDirection.BUY
        print(f"Opposite side: {order.direction}")
        print(f"Opposite side: {opposite_side}")
        stmt = (
            select(Order)
            .where(
                and_(
                    Order.instrument_ticker == order.instrument_ticker,
                    Order.direction == opposite_side,
                    Order.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
                    Order.price.isnot(None),
                    Order.type == OrderType.LIMIT,
                )
            )
            .order_by(
                Order.price.asc() if order.direction == Direction.BUY else Order.price.desc(),
                Order.timestamp.asc()
            )
        )
        result = await session.execute(stmt)
        matching_orders = result.scalars().all()

        if not matching_orders:
            return


        remaining_qty = order.qty - order.filled

        for counter_order in matching_orders:

            print(f"Order: {counter_order.type, counter_order.direction}")
            if remaining_qty == 0:
                break
            if counter_order.price is None:
                    continue
            
            available_qty = counter_order.qty - counter_order.filled
            trade_qty = min(remaining_qty, available_qty)
            trade_price = counter_order.price
            print(f"Order: {order.type, order.direction}")
            if order.direction == OrderDirection.BUY:
                buyer_id = order.user_id
                seller_id = counter_order.user_id
            else:
                buyer_id = counter_order.user_id
                seller_id = order.user_id

            try:
                
                initial_locked_price = counter_order.price if counter_order.price is not None else trade_price

                await apply_trade(
                    session,
                    buyer_id,
                    seller_id,
                    order.instrument_ticker,
                    trade_price,
                    trade_qty,
                    initial_locked_price
                )
                await execute_trade(session, order, counter_order, trade_qty, trade_price)
            except Exception as e:
                raise  # ошибка поднимется наверх и откатит всю транзакцию

            counter_order.filled += trade_qty
            counter_order.status = (
                OrderStatus.EXECUTED if counter_order.filled == counter_order.qty
                else OrderStatus.PARTIALLY_EXECUTED
            )

            remaining_qty -= trade_qty

        order.filled = order.qty - remaining_qty
        if order.filled == order.qty:
            order.status = OrderStatus.EXECUTED
        elif order.filled > 0:
            order.status = OrderStatus.PARTIALLY_EXECUTED
        else:
            order.status = OrderStatus.CANCELLED

        await session.flush()

    except Exception as e:
        order.status = OrderStatus.CANCELLED
        raise
    finally:
        if order.filled == 0 and order.status == OrderStatus.NEW:
            order.status = OrderStatus.CANCELLED


async def execute_trade(
    session: AsyncSession,
    order1: models.Order,
    order2: models.Order,
    qty: float,
    price: float,
):
    await create_transaction(order1, order2, qty, price, session)
