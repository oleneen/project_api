from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .. import models, schemas
from .. import schemas, models, crud
from ..crud.users import get_user_by_token
from ..crud.instruments import get_instrument_by_ticker
from ..crud.balances import update_user_balance,get_user_balance
import logging

logger = logging.getLogger(__name__) 

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

async def create_order(db: AsyncSession, order: schemas.LimitOrderBody | schemas.MarketOrderBody, user_id: str):
    db_order = models.Order(
        user_id=user_id,
        **order.dict()
    )
    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)
    return db_order

async def process_market_order(
    db: AsyncSession,
    order: schemas.MarketOrderBody,
    user_id: str
):
    """
    Обрабатывает рыночный ордер:
    1. Проверяет наличие инструмента
    2. Для BUY ордеров:
       - Находит все ASK ордера (на продажу) с лучшими ценами
       - Исполняет их пока не исполнится весь объем или не закончатся подходящие ордера
    3. Для SELL ордеров:
       - Находит все BID ордера (на покупку) с лучшими ценами
       - Исполняет их пока не исполнится весь объем или не закончатся подходящие ордера
    4. Обновляет балансы пользователей
    5. Возвращает информацию об исполнении
    """
    # Проверяем существование инструмента
    instrument = await get_instrument_by_ticker(db, order.ticker)
    if not instrument:
        raise ValueError(f"Инструмент {order.ticker} не найден")

    # Создаем запись ордера в базе
    db_order = await create_order(db, order, user_id)
    remaining_qty = order.qty
    total_executed = 0
    avg_price = 0

    # Определяем направление поиска противоположных ордеров
    if order.direction == "BUY":
        # Для покупки ищем ордера на продажу (ASK), сортируем по возрастанию цены
        opposite_direction = "SELL"
        order_by = models.Order.price.asc()
    else:
        # Для продажи ищем ордера на покупку (BID), сортируем по убыванию цены
        opposite_direction = "BUY"
        order_by = models.Order.price.desc()

    # Получаем список противоположных ордеров
    while remaining_qty > 0:
        opposite_orders = await db.execute(
            select(models.Order)
            .where(
                models.Order.ticker == order.ticker,
                models.Order.direction == opposite_direction,
                models.Order.status == "NEW"
            )
            .order_by(order_by)
        )
        opposite_orders = opposite_orders.scalars().all()

        if not opposite_orders:
            break  # Нет подходящих ордеров для исполнения

        for opposite_order in opposite_orders:
            if remaining_qty <= 0:
                break

            # Определяем сколько можем исполнить в этом ордере
            available_qty = opposite_order.qty - opposite_order.filled
            executed_qty = min(available_qty, remaining_qty)

            # Обновляем ордера
            opposite_order.filled += executed_qty
            if opposite_order.filled >= opposite_order.qty:
                opposite_order.status = "FILLED"

            db_order.filled += executed_qty
            if db_order.filled >= db_order.qty:
                db_order.status = "FILLED"

            # Обновляем балансы пользователей
            if order.direction == "BUY":
                # Покупатель получает инструмент, отдает деньги
                # Продавец получает деньги, отдает инструмент
                await crud.update_user_balance(db, user_id, order.ticker, executed_qty)
                await update_user_balance(db, opposite_order.user_id, order.ticker, -executed_qty)
                await update_user_balance(db, user_id, "USD", -executed_qty * opposite_order.price)
                await update_user_balance(db, opposite_order.user_id, "USD", executed_qty * opposite_order.price)
            else:
                # Продавец отдает инструмент, получает деньги
                # Покупатель получает инструмент, отдает деньги
                await update_user_balance(db, user_id, order.ticker, -executed_qty)
                await update_user_balance(db, opposite_order.user_id, order.ticker, executed_qty)
                await update_user_balance(db, user_id, "USD", executed_qty * opposite_order.price)
                await update_user_balance(db, opposite_order.user_id, "USD", -executed_qty * opposite_order.price)

            total_executed += executed_qty
            avg_price = (avg_price * (total_executed - executed_qty) + opposite_order.price * executed_qty) / total_executed
            remaining_qty -= executed_qty

        await db.commit()

    # Обновляем статус ордера
    if db_order.filled > 0:
        if db_order.filled < db_order.qty:
            db_order.status = "PARTIALLY_FILLED"
        await db.commit()
        await db.refresh(db_order)

    return {
        "order": db_order,
        "executed_qty": total_executed,
        "avg_price": avg_price if total_executed > 0 else None
    }


async def process_market_order(db: AsyncSession, order_data: schemas.MarketOrderBody, user_id: str):
    try:
        # Проверяем инструмент
        instrument = await get_instrument_by_ticker(db, order_data.ticker)
        if not instrument:
            raise ValueError(f"Инструмент {order_data.ticker} не найден")

        # Создаем ордер (указываем статус явно!)
        db_order = models.Order(
            user_id=user_id,
            direction=order_data.direction,
            instrument_ticker=order_data.ticker,
            qty=order_data.qty,
            price=None,  # Для рыночного ордера цена не указывается
            type="MARKET",
            status="NEW",  # Важно: статус не должен быть NULL!
            filled=0
        )
        db.add(db_order)
        await db.commit()
        await db.refresh(db_order)
        
        return db_order

    except Exception as e:
        await db.rollback()
        raise ValueError(f"Ошибка при создании ордера: {str(e)}")
    
async def process_limit_order(
    db: AsyncSession,
    order_data: schemas.LimitOrderBody,
    authorization: str  # Принимаем заголовок авторизации вместо user_id
):
    """
    Создает лимитный ордер, используя токен авторизации для поиска пользователя
    """
    # Проверяем токен и получаем пользователя
    if not authorization or not authorization.startswith("TOKEN "):
        raise ValueError("Неверный формат токена авторизации")
    
    token = authorization.split(" ")[1]
    user = await get_user_by_token(db, token)
    if not user:
        raise ValueError("Пользователь не найден")

    # Проверка инструмента
    instrument = await get_instrument_by_ticker(db, order_data.ticker)
    if not instrument:
        raise ValueError(f"Инструмент {order_data.ticker} не найден")

    # Определяем нужный тикер для проверки баланса
    balance_ticker = "RUB" if order_data.direction == "BUY" else order_data.ticker
    required_amount = order_data.price * order_data.qty if order_data.direction == "BUY" else order_data.qty

    # Проверка баланса
    balance = await get_user_balance(db, str(user.id), balance_ticker)
    if balance < required_amount:
        error_msg = (f"Недостаточно {'RUB' if order_data.direction == 'BUY' else order_data.ticker} "
                    f"(требуется: {required_amount}, доступно: {balance})")
        raise ValueError(error_msg)

    # Создание ордера
    db_order = models.Order(
        user_id=user.id,
        direction=order_data.direction,
        instrument_ticker=order_data.ticker,
        qty=order_data.qty,
        price=order_data.price,
        type="LIMIT",
        status="NEW",
        filled=0
    )
    
    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)
    
    return db_order