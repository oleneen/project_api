from sqlalchemy import select, update,and_
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from .. import models
from ..schemas import HTTPValidationError
from ..models import User, OrderStatus, Balance
import logging
import asyncio
from sqlalchemy.exc import OperationalError

MAX_RETRIES = 3

logger = logging.getLogger(__name__)
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
    retries = 0
    while retries < MAX_RETRIES:
        try:
            result = await db.execute(
                update(models.Balance)
                .where(
                    models.Balance.user_id == user_id,
                    models.Balance.instrument_ticker == ticker,
                    (models.Balance.amount - models.Balance.locked) >= amount
                )
                .values(locked=models.Balance.locked + amount)
                .returning(models.Balance)
            )
            updated_balance = result.fetchone()
            if not updated_balance:
                raise HTTPException(status_code=400, detail=f"Недостаточно свободных средств для блокировки {amount} {ticker}")
            await db.commit()
            return updated_balance
        except OperationalError as e:
            # Проверяем, что ошибка — deadlock
            if "deadlock detected" in str(e):
                retries += 1
                await asyncio.sleep(0.1 * retries)  # небольшой бэк-офф
                continue
            else:
                raise
    raise HTTPException(status_code=500, detail="Сервер перегружен, попробуйте позже")

async def update_user_balance(db: AsyncSession, user_id: str, ticker: str, amount: int):
    retries = 0
    while retries < MAX_RETRIES:
        try:
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
        except OperationalError as e:
            if "deadlock detected" in str(e):
                retries += 1
                logger.warning(f"Deadlock detected in update_user_balance, retry {retries}")
                await asyncio.sleep(0.1 * retries)
                continue
            else:
                raise
    raise HTTPException(status_code=500, detail="Сервер перегружен, попробуйте позже")



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
    retries = 0
    while retries < MAX_RETRIES:
        try:
            await db.execute(
                update(Balance)
                .where(Balance.user_id == user_id, Balance.instrument_ticker == ticker)
                .values(locked=Balance.locked - amount)
            )
            await db.commit()
            return
        except OperationalError as e:
            if "deadlock detected" in str(e):
                retries += 1
                logger.warning(f"Deadlock detected in unlock_user_balance, retry {retries}")
                await asyncio.sleep(0.1 * retries)
                continue
            else:
                raise
    raise HTTPException(status_code=500, detail="Сервер перегружен, попробуйте позже")
    

async def apply_trade(
    db: AsyncSession,
    buyer_id: str,
    seller_id: str,
    ticker: str,
    price: int,
    quantity: int,
    initial_locked_price: int
):
    retries = 0
    total_cost = price * quantity
    if initial_locked_price is None:
        raise ValueError("initial_locked_price не должен быть None")
    initial_total_locked = initial_locked_price * quantity

    while retries < MAX_RETRIES:
        try:
            # Здесь НЕ открываем новую транзакцию,
            # предполагается, что вызывающий код уже обернул вызов в транзакцию.

            # Получаем балансы с блокировкой в фиксированном порядке
            buyer_rub = await db.scalar(
                select(Balance).where(
                    Balance.user_id == buyer_id,
                    Balance.instrument_ticker == "RUB"
                ).with_for_update()
            )
            if not buyer_rub or buyer_rub.locked < initial_total_locked:
                raise HTTPException(400, detail="Недостаточно залоченных средств у покупателя")

            seller_rub = await db.scalar(
                select(Balance).where(
                    Balance.user_id == seller_id,
                    Balance.instrument_ticker == "RUB"
                ).with_for_update()
            )

            buyer_asset = await db.scalar(
                select(Balance).where(
                    Balance.user_id == buyer_id,
                    Balance.instrument_ticker == ticker
                ).with_for_update()
            )

            seller_asset = await db.scalar(
                select(Balance).where(
                    Balance.user_id == seller_id,
                    Balance.instrument_ticker == ticker
                ).with_for_update()
            )
            if not seller_asset or seller_asset.locked < quantity:
                raise HTTPException(400, detail="Недостаточно залоченных активов у продавца")

            # Обновляем балансы
            buyer_rub.locked -= initial_total_locked
            buyer_rub.amount -= total_cost

            if buyer_asset:
                buyer_asset.amount += quantity
            else:
                db.add(Balance(
                    user_id=buyer_id,
                    instrument_ticker=ticker,
                    amount=quantity,
                    locked=0
                ))

            seller_asset.locked -= quantity
            seller_asset.amount -= quantity

            if seller_rub:
                seller_rub.amount += total_cost
            else:
                db.add(Balance(
                    user_id=seller_id,
                    instrument_ticker="RUB",
                    amount=total_cost,
                    locked=0
                ))

            # Важно — НЕ коммитим здесь, это сделает вызывающий код.

            return

        except OperationalError as e:
            if "deadlock detected" in str(e):
                retries += 1
                logger.warning(f"Deadlock detected in apply_trade (retry {retries})")
                await asyncio.sleep(0.1 * retries)
                continue
            raise
        except HTTPException:
            raise
        except Exception:
            logger.exception("Unexpected error during apply_trade")
            raise HTTPException(500, detail="Ошибка на сервере при применении сделки")

    raise HTTPException(500, detail="Сервер перегружен. Повторите попытку позже.")