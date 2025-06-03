from sqlalchemy import select, update,and_
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from .. import models
from ..schemas import HTTPValidationError

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
        new_amount = balance.amount + amount

        if new_amount < balance.locked:
            raise ValueError("Недостаточно доступных средств (учитывая заблокированные)")

        balance.amount = new_amount

        if balance.amount == 0 and balance.locked == 0:
            await db.delete(balance)

    else:
        if amount < 0:
            raise ValueError("Нельзя снять средства с несуществующего баланса")
        balance = models.Balance(
            user_id=str(user_id),
            instrument_ticker=ticker,
            amount=amount,
            locked=0  
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
    
async def transfer_balance(
    session: AsyncSession,
    from_user_id: str,
    to_user_id: str,
    amount: float,
    ticker: str = "RUB"  
) -> None:
    if amount <= 0:
        raise ValueError("Transfer amount must be positive")

    sender_stmt = select(models.Balance).where(
        and_(models.Balance.user_id == from_user_id, models.Balance.instrument_ticker == ticker)
    )
    sender_result = await session.execute(sender_stmt)
    sender_balance = sender_result.scalar_one_or_none()

    if not sender_balance or sender_balance.amount < amount:
        raise HTTPValidationError(status_code=400, detail="Insufficient funds")

    receiver_stmt = select(models.Balance).where(
        and_(models.Balance.user_id == to_user_id, models.Balance.instrument_ticker == ticker)
    )
    receiver_result = await session.execute(receiver_stmt)
    receiver_balance = receiver_result.scalar_one_or_none()

    sender_balance.amount -= amount

    if receiver_balance:
        receiver_balance.amount += amount
    else:
        new_balance = models.Balance(
            user_id=to_user_id,
            instrument_ticker=ticker,
            amount=amount
        )
        session.add(new_balance)
