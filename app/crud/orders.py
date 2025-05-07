from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .. import models

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
