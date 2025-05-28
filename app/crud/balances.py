from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from .. import models

async def get_user_balances(db: AsyncSession, user_id: str):
    result = await db.execute(
        select(models.Balance.instrument_ticker, models.Balance.amount)
        .where(models.Balance.user_id == user_id)
    )
    return result.all()

async def get_available_balance(db: AsyncSession, user_id: str, ticker: str) -> int:
    result = await db.execute(
        select(models.Balance.amount, models.Balance.locked)
        .where(models.Balance.user_id == user_id, models.Balance.instrument_ticker == ticker)
    )
    row = result.first()
    if not row:
        return 0
    amount, locked = row
    return amount - locked

async def lock_user_balance(db: AsyncSession, user_id: str, ticker: str, amount: int):
    await db.execute(
        update(models.Balance)
        .where(models.Balance.user_id == user_id, models.Balance.instrument_ticker == ticker)
        .values(locked=models.Balance.locked + amount)
    )

async def update_user_balance(db: AsyncSession, user_id: str, ticker: str, amount: int):
    result = await db.execute(
        select(models.Balance).where(
            models.Balance.user_id == str(user_id),
            models.Balance.instrument_ticker == ticker
        )
    )
    balance = result.scalar_one_or_none()

    if balance:
        balance.amount += amount

        if balance.amount == 0:
            await db.delete(balance)
        elif balance.amount < 0:
            raise ValueError("Недостаточно средств")
    else:
        if amount < 0:
            raise ValueError("Нельзя снять средства с несуществующего баланса")
        balance = models.Balance(
            user_id=str(user_id),
            instrument_ticker=ticker,
            amount=amount
        )
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

async def unlock_user_balance(db: AsyncSession, user_id: str, ticker: str, amount: int):
    await db.execute(
        update(models.Balance)
        .where(models.Balance.user_id == user_id, models.Balance.instrument_ticker == ticker)
        .values(locked=models.Balance.locked + amount)
    )
    