from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from .. import schemas, models, crud
from ..database import get_db

router = APIRouter()

async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    if not authorization.startswith("TOKEN "):
        raise HTTPException(status_code=401, detail="Invalid token format")
    token = authorization[6:]
    user = await crud.get_user_by_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

@router.post("/instrument", response_model=schemas.Ok)
async def add_instrument(
    instrument: schemas.Instrument,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Требуются права администратора")
    
    db_instrument = await crud.get_instrument_by_ticker(db, instrument.ticker)
    if db_instrument:
        raise HTTPException(status_code=400, detail="Инструмент уже существует")
    
    await crud.create_instrument(db, instrument)
    return {"success": True}
# Эндпоинт для пополнения баланса пользователя
# @router.post("/balance/deposit")
# def deposit_balance(operation: BalanceOperation, db: Session = Depends(get_db)):
#     """
#     Пополняет баланс пользователя.
#     Только для администраторов.
    
#     Параметры:
#     - operation: Данные операции (user_id, ticker, amount)
#     - db: Сессия базы данных
    
#     Возвращает:
#     - Обновленный баланс
#     """
#     return crud.create_user_balance(
#         db, 
#         user_id=operation.user_id,
#         ticker=operation.ticker,
#         amount=operation.amount
#     )

# # Функция для проверки и получения текущего пользователя
# def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)):
#     """
#     Проверяет и извлекает пользователя по токену авторизации.
    
#     Параметры:
#     - authorization: Заголовок Authorization в формате "TOKEN <token>"
#     - db: Сессия базы данных
    
#     Возвращает:
#     - Объект пользователя
    
#     Исключения:
#     - 401: Если формат токена неверный или пользователь не найден
#     """
#     if not authorization.startswith("TOKEN "):
#         raise HTTPException(status_code=401, detail="Invalid token format")
#     token = authorization[6:]  # Извлекаем токен после "TOKEN "
#     user = crud.get_user_by_token(db, token)
#     if not user:
#         raise HTTPException(status_code=401, detail="Invalid token")
#     return user

# # Эндпоинт для получения балансов пользователя
# @router.get("/balance")
# def get_balances(
#     current_user: models.User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Получает все балансы текущего пользователя.
    
#     Параметры:
#     - current_user: Текущий авторизованный пользователь
#     - db: Сессия базы данных
    
#     Возвращает:
#     - Список балансов пользователя
#     """
#     return crud.get_user_balances(db, current_user.id)

# # Эндпоинт для создания ордера
# @router.post("/order")
# def create_order(
#     order_data: schemas.LimitOrderBody | schemas.MarketOrderBody,
#     current_user: models.User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Создает новый ордер (лимитный или рыночный).
    
#     Параметры:
#     - order_data: Данные ордера (тип, тикер, количество, цена для лимитного)
#     - current_user: Текущий авторизованный пользователь
#     - db: Сессия базы данных
    
#     Возвращает:
#     - Созданный ордер
#     """
#     return crud.create_order(db, current_user.id, order_data)

# # Эндпоинт для получения списка ордеров пользователя
# @router.get("/order")
# def list_orders(
#     current_user: models.User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Получает список всех активных ордеров пользователя.
    
#     Параметры:
#     - current_user: Текущий авторизованный пользователь
#     - db: Сессия базы данных
    
#     Возвращает:
#     - Список ордеров пользователя
#     """
#     return crud.get_user_orders(db, current_user.id)

# # Эндпоинт для удаления пользователя
# @router.delete("/user/{user_id}")
# def delete_user(
#     user_id: str,
#     current_user: models.User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """
#     Удаляет пользователя и все связанные данные.
#     Только для администраторов.
    
#     Параметры:
#     - user_id: ID пользователя для удаления
#     - current_user: Текущий авторизованный пользователь (проверка прав)
#     - db: Сессия базы данных
    
#     Возвращает:
#     - Статус операции
    
#     Исключения:
#     - 403: Если у текущего пользователя нет прав администратора
#     - 404: Если пользователь не найден
#     """
#     # Проверка прав администратора
#     if current_user.role != "ADMIN":
#         raise HTTPException(status_code=403, detail="Требуются права администратора")
    
#     # Поиск пользователя
#     db_user = db.query(models.User).filter(models.User.id == user_id).first()
#     if not db_user:
#         raise HTTPException(status_code=404, detail="Пользователь не найден")
    
#     # Удаление связанных данных в транзакции
#     # 1. Удаляем все ордера пользователя
#     db.query(models.Order).filter(models.Order.user_id == user_id).delete()
#     # 2. Удаляем все балансы пользователя
#     db.query(models.Balance).filter(models.Balance.user_id == user_id).delete()
#     # 3. Удаляем самого пользователя
#     db.delete(db_user)
#     db.commit()  # Фиксируем изменения
    
#     return {"status": "ok", "message": f"Пользователь {user_id} удален"}

# @router.delete("/admin/instrument/{ticker}", response_model=schemas.Ok)
# async def delete_instrument(
#     ticker: str,
#     current_user: models.User = Depends(get_current_admin),
#     db: AsyncSession = Depends(get_db)
# ):
#     """
#     Удаляет инструмент и все связанные с ним ордера.
#     Требует прав администратора.
#     """
#     try:
#         # Находим инструмент
#         result = await db.execute(
#             select(models.Instrument)
#             .where(models.Instrument.ticker == ticker)
#         )
#         instrument = result.scalar_one_or_none()
        
#         if not instrument:
#             raise HTTPException(
#                 status_code=404,
#                 detail=f"Инструмент {ticker} не найден"
#             )

#         # Удаляем связанные ордера
#         await db.execute(
#             delete(models.Order)
#             .where(models.Order.instrument_id == instrument.ticker)
#         )

#         # Удаляем сам инструмент
#         await db.delete(instrument)
#         await db.commit()
        
#         return {"success": True, "message": f"Инструмент {ticker} удален"}
    
#     except Exception as e:
#         await db.rollback()
#         logger.error(f"Error deleting instrument: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail="Ошибка при удалении инструмента"
#         )
# @router.post("/balance/withdraw", response_model=schemas.Ok)
# def withdraw_balance(
#         operation: schemas.WithdrawRequest,
#         current_user: models.User = Depends(get_current_user),
#         db: Session = Depends(get_db)
# ):
#     """
#     Списание средств с баланса пользователя.
#     Только для администраторов.

#     Параметры:
#     - user_id: UUID пользователя
#     - ticker: Тикер инструмента
#     - amount: Сумма списания (должна быть > 0)

#     Возвращает:
#     - {"success": true} при успешном списании

#     Исключения:
#     - 403: Нет прав администратора
#     - 400: Недостаточно средств или баланс не найден
#     """
#     if current_user.role != "ADMIN":
#         raise HTTPException(status_code=403, detail="Требуются права администратора")

#     try:
#         # Проверяем существование баланса
#         balance = db.query(models.Balance).filter(
#             models.Balance.user_id == operation.user_id,
#             models.Balance.ticker == operation.ticker
#         ).first()

#         if not balance:
#             raise HTTPException(status_code=400, detail="Balance not found")

#         if balance.amount < operation.amount:
#             raise HTTPException(status_code=400, detail=f"Недостаточно средств. Текущий баланс: {balance.amount}")

#         # Списание средств
#         balance.amount -= operation.amount
#         db.commit()
#         return {"success": True}

#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=400, detail=str(e))