from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from . import models, schemas

async def get_user_by_token(db: AsyncSession, token: str):
    result = await db.execute(
        select(models.User).where(models.User.api_key == token)
    )
    return result.scalar_one_or_none()

async def create_instrument(db: AsyncSession, instrument: schemas.Instrument):
    db_instrument = models.Instrument(**instrument.dict())
    db.add(db_instrument)
    await db.commit()
    await db.refresh(db_instrument)
    return db_instrument

async def get_instruments(db: AsyncSession):
    result = await db.execute(select(models.Instrument))
    return result.scalars().all()

async def get_instrument_by_ticker(db: AsyncSession, ticker: str):
    """
    Получает инструмент из базы данных по его тикеру.
    
    Параметры:
        db: Асинхронная сессия SQLAlchemy
        ticker: Тикер инструмента (например, "BTC")
    
    Возвращает:
        Объект Instrument или None, если инструмент не найден
    """
    result = await db.execute(
        select(models.Instrument).where(models.Instrument.ticker == ticker)
    )
    return result.scalar_one_or_none()

async def create_user_balance(db: AsyncSession, user_id: str, ticker: str, amount: int):
    balance = models.Balance(user_id=user_id, ticker=ticker, amount=amount)
    db.add(balance)
    await db.commit()
    return balance

async def get_user_balances(db: AsyncSession, user_id: str):
    result = await db.execute(
        select(models.Balance.ticker, models.Balance.amount)
        .where(models.Balance.user_id == user_id)
    )
    return result.all()  # Вернет список кортежей (ticker, amount)

async def create_order(db: AsyncSession, order: schemas.LimitOrderBody | schemas.MarketOrderBody, user_id: str):
    db_order = models.Order(
        user_id=user_id,
        **order.dict()
    )
    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)
    return db_order

async def get_order_by_id(db: AsyncSession, order_id: str, user_id: str = None):
    stmt = select(models.Order).where(models.Order.id == order_id)
    if user_id:
        stmt = stmt.where(models.Order.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def withdraw_balance(db: AsyncSession, user_id: str, ticker: str, amount: int):
    result = await db.execute(
        select(models.Balance).where(
            models.Balance.user_id == user_id,
            models.Balance.ticker == ticker
        )
    )
    balance = result.scalar_one_or_none()
    
    if not balance:
        raise ValueError("Balance not found")
    
    if balance.amount < amount:
        raise ValueError("Insufficient funds")
    
    balance.amount -= amount
    await db.commit()
    return balance

async def get_orderbook_data(db: AsyncSession, ticker: str, limit: int = 10):
    """
    Получает стакан заявок для указанного тикера.
    Возвращает:
        - dict с bids и asks, если есть заявки
        - None, если нет ни одной заявки
        - raises Exception, если инструмент не найден
    """
    # Проверяем существование инструмента
    instrument = await db.execute(
        select(models.Instrument).where(models.Instrument.ticker == ticker)
    )
    if not instrument.scalar_one_or_none():
        raise ValueError(f"Инструмент {ticker} не найден")

    # Получаем заявки на покупку (BID)
    bids_result = await db.execute(
        select(models.Order)
        .where(
            models.Order.ticker == ticker,
            models.Order.direction == "BUY",
            models.Order.status == "NEW"
        )
        .order_by(models.Order.price.desc())
        .limit(limit)
    )
    bids = [{"price": o.price, "qty": o.qty} for o in bids_result.scalars().all()]

    # Получаем заявки на продажу (ASK)
    asks_result = await db.execute(
        select(models.Order)
        .where(
            models.Order.ticker == ticker,
            models.Order.direction == "SELL",
            models.Order.status == "NEW"
        )
        .order_by(models.Order.price.asc())
        .limit(limit)
    )
    asks = [{"price": o.price, "qty": o.qty} for o in asks_result.scalars().all()]

    # Если нет ни одной заявки - возвращаем None
    if not bids and not asks:
        return None

    return {
        "bids": bids,
        "asks": asks
    }

