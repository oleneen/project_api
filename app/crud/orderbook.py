from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from .. import models
from ..schemas import Level, L2OrderBook
from typing import Optional

async def get_orderbook_data(db: AsyncSession, ticker: str, limit: int = 10) -> Optional[L2OrderBook]:

    bids_result = await db.execute(
        select(
            models.Order.price,
            (models.Order.qty - models.Order.filled).label("remaining_qty")
        )
        .where(
            models.Order.instrument_ticker == ticker,
            models.Order.direction == models.OrderDirection.BUY,
            models.Order.status == models.OrderStatus.NEW,
            models.Order.type == models.OrderType.LIMIT
        )
        .order_by(
            models.Order.price.desc(),
            models.Order.timestamp.asc()
        )
        .limit(limit)
    )
    bids = [Level(price=price, qty=int(qty)) for price, qty in bids_result]

    asks_result = await db.execute(
        select(
            models.Order.price,
            (models.Order.qty - models.Order.filled).label("remaining_qty")
        )
        .where(
            models.Order.instrument_ticker == ticker,
            models.Order.direction == models.OrderDirection.SELL,
            models.Order.status == models.OrderStatus.NEW,
            models.Order.type == models.OrderType.LIMIT
        )
        .order_by(
            models.Order.price.asc(),
            models.Order.timestamp.asc()
        )
        .limit(limit)
    )
    asks = [Level(price=price, qty=int(qty)) for price, qty in asks_result]

    if not bids and not asks:
        return None

    return L2OrderBook(
        bid_levels=bids,
        ask_levels=asks
    )