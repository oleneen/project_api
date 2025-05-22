from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .. import models


async def get_transactions(db: AsyncSession, ticker: str, limit: int = 10):
    result = await db.execute(
        select(models.Transaction).where(
            models.Transaction.ticker == ticker
        )
        .limit(limit)
    )
    return result.scalars().all()


async def create_transaction(order: models.Order, opposite_order: models.Order, qty: int, db: AsyncSession):
    if order.direction == "BUY":
        buyer_order = order
        seller_order = opposite_order
    else:
        buyer_order = opposite_order
        seller_order = order

    transaction = models.Transaction(
        ticker=order.instrument_ticker,
        qty=qty,
        price=seller_order.price,
        buy_order_id=buyer_order.id,
        sell_order_id=seller_order.id,
    )

    db.add(transaction)
