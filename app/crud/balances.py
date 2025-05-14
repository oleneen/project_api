from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from .. import models

async def get_user_balances(db: AsyncSession, user_id: str):
    result = await db.execute(
        select(models.Balance.instrument_ticker, models.Balance.amount)
        .where(models.Balance.user_id == user_id)
    )
    return result.all()

async def update_user_balance(db: AsyncSession, user_id: str, ticker: str, amount: int):
    result = await db.execute(
        select(models.Balance).where(
            models.Balance.user_id == str(user_id),
            models.Balance.instrument_ticker== ticker
        )
    )

    balance = result.scalar_one_or_none()

    if balance:
        balance.amount += amount
    else:
        if amount < 0:
            raise ValueError("Недостаточно средств")
        balance = models.Balance(user_id=str(user_id), instrument_ticker=ticker, amount=amount)
        db.add(balance)

    await db.commit()
    return balance

async def get_user_balance(db: AsyncSession, user_id: UUID, ticker: str) -> int:
    result = await db.execute(
        select(models.Balance.amount).where(
            models.Balance.user_id == user_id,
            models.Balance.instrument_ticker == ticker
        )
    )
    balance = result.scalar()
    return balance if balance is not None else 0