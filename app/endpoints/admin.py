from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from .. import schemas, models, crud
from ..database import get_db

# Создаем роутер для API с префиксом /api/v1
router = APIRouter(prefix="/api/v1")
from ..schemas import BalanceOperation

# Эндпоинт для добавления нового инструмента
@router.post("/instrument")
def add_instrument(instrument: schemas.Instrument, db: Session = Depends(get_db)):
    """
    Добавляет новый торговый инструмент в систему.
    Требует прав администратора (проверяется в get_current_user).
    
    Параметры:
    - instrument: Данные инструмента (название и тикер)
    - db: Сессия базы данных
    
    Возвращает:
    - Созданный инструмент
    """
    return crud.create_instrument(db, instrument)

# Эндпоинт для пополнения баланса пользователя
@router.post("/balance/deposit")
def deposit_balance(operation: BalanceOperation, db: Session = Depends(get_db)):
    """
    Пополняет баланс пользователя.
    Только для администраторов.
    
    Параметры:
    - operation: Данные операции (user_id, ticker, amount)
    - db: Сессия базы данных
    
    Возвращает:
    - Обновленный баланс
    """
    return crud.create_user_balance(
        db, 
        user_id=operation.user_id,
        ticker=operation.ticker,
        amount=operation.amount
    )

# Функция для проверки и получения текущего пользователя
def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)):
    """
    Проверяет и извлекает пользователя по токену авторизации.
    
    Параметры:
    - authorization: Заголовок Authorization в формате "TOKEN <token>"
    - db: Сессия базы данных
    
    Возвращает:
    - Объект пользователя
    
    Исключения:
    - 401: Если формат токена неверный или пользователь не найден
    """
    if not authorization.startswith("TOKEN "):
        raise HTTPException(status_code=401, detail="Invalid token format")
    token = authorization[6:]  # Извлекаем токен после "TOKEN "
    user = crud.get_user_by_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

# Эндпоинт для получения балансов пользователя
@router.get("/balance")
def get_balances(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получает все балансы текущего пользователя.
    
    Параметры:
    - current_user: Текущий авторизованный пользователь
    - db: Сессия базы данных
    
    Возвращает:
    - Список балансов пользователя
    """
    return crud.get_user_balances(db, current_user.id)

# Эндпоинт для создания ордера
@router.post("/order")
def create_order(
    order_data: schemas.LimitOrderBody | schemas.MarketOrderBody,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Создает новый ордер (лимитный или рыночный).
    
    Параметры:
    - order_data: Данные ордера (тип, тикер, количество, цена для лимитного)
    - current_user: Текущий авторизованный пользователь
    - db: Сессия базы данных
    
    Возвращает:
    - Созданный ордер
    """
    return crud.create_order(db, current_user.id, order_data)

# Эндпоинт для получения списка ордеров пользователя
@router.get("/order")
def list_orders(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получает список всех активных ордеров пользователя.
    
    Параметры:
    - current_user: Текущий авторизованный пользователь
    - db: Сессия базы данных
    
    Возвращает:
    - Список ордеров пользователя
    """
    return crud.get_user_orders(db, current_user.id)

# Эндпоинт для удаления пользователя
@router.delete("/user/{user_id}")
def delete_user(
    user_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Удаляет пользователя и все связанные данные.
    Только для администраторов.
    
    Параметры:
    - user_id: ID пользователя для удаления
    - current_user: Текущий авторизованный пользователь (проверка прав)
    - db: Сессия базы данных
    
    Возвращает:
    - Статус операции
    
    Исключения:
    - 403: Если у текущего пользователя нет прав администратора
    - 404: Если пользователь не найден
    """
    # Проверка прав администратора
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Требуются права администратора")
    
    # Поиск пользователя
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Удаление связанных данных в транзакции
    # 1. Удаляем все ордера пользователя
    db.query(models.Order).filter(models.Order.user_id == user_id).delete()
    # 2. Удаляем все балансы пользователя
    db.query(models.Balance).filter(models.Balance.user_id == user_id).delete()
    # 3. Удаляем самого пользователя
    db.delete(db_user)
    db.commit()  # Фиксируем изменения
    
    return {"status": "ok", "message": f"Пользователь {user_id} удален"}

# Эндпоинт для удаления инструмента (делистинг)
@router.delete("/instrument/{ticker}")
def delist_instrument(
    ticker: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Удаляет инструмент из системы и отменяет все связанные ордера.
    Только для администраторов.
    
    Параметры:
    - ticker: Тикер инструмента для удаления
    - current_user: Текущий авторизованный пользователь (проверка прав)
    - db: Сессия базы данных
    
    Возвращает:
    - Статус операции
    
    Исключения:
    - 403: Если у текущего пользователя нет прав администратора
    - 404: Если инструмент не найден
    """
    # Проверка прав администратора
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Требуются права администратора")
    
    # Поиск инструмента
    instrument = db.query(models.Instrument).filter(models.Instrument.ticker == ticker).first()
    if not instrument:
        raise HTTPException(status_code=404, detail="Инструмент не найден")
    
    # Отмена всех активных ордеров по этому инструменту
    db.query(models.Order).filter(
        models.Order.ticker == ticker,
        models.Order.status == "NEW"  # Только активные ордера
    ).update({"status": "CANCELLED"})  # Массовое обновление
    
    # Удаление инструмента
    db.delete(instrument)
    db.commit()  # Фиксируем изменения
    
    return {"status": "ok", "message": f"Инструмент {ticker} удален"}