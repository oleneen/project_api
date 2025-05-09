from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from ..database import get_db
from ..models import User
import logging
from ..schemas import OrderResponse
from ..dependencies.auth import get_current_user
from ..crud import get_orders_by_user_id
from .. import schemas  # Импорт модуля schemas
from ..crud import (  # Импорт всех необходимых функций из crud
    get_user_by_token,
    process_market_order,
    process_limit_order  # Добавлен импорт process_limit_order
)
from ..schemas import MarketOrderBody, LimitOrderBody  # Явный импорт нужных схем

router = APIRouter(prefix="/api/v1")  # Добавьте prefix

# Инициализация логгера
logger = logging.getLogger(__name__)

# Модель для ответа
class OrderResponse(schemas.OrderResponse):  # Наследуемся от схемы из schemas.py
    class Config:
        from_attributes = True

@router.post("/market-order")
async def create_market_order(
    order: MarketOrderBody,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Создание рыночного ордера"""
    # Проверка авторизации
    if not authorization or not authorization.startswith("TOKEN "):
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    api_key = authorization.split(" ")[1]
    
    # Получаем пользователя
    user = await get_user_by_token(db, api_key)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        result = await process_market_order(db, order, str(user.id))
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Market order error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/limit-order")
async def create_limit_order(
    order: schemas.LimitOrderBody,
    authorization: str = Header(...),  # Получаем токен из заголовка
    db: AsyncSession = Depends(get_db)
):
    """Создание лимитного ордера"""
    try:
        # Передаем authorization вместо user_id
        result = await process_limit_order(db, order, authorization)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Limit order error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
        
@router.get("/orders", response_model=List[OrderResponse])
async def get_user_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await get_orders_by_user_id(db, str(current_user.id))
