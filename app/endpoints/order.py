from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Union
from ..database import get_db
from ..models import User
import logging
from ..schemas import CreateOrderResponse, LimitOrder, MarketOrder, LimitOrderBody, MarketOrderBody
from ..dependencies.user import get_authenticated_user
from ..crud import get_orders_by_user_id
from .. import schemas
from ..crud import (
    get_user_by_token,
    process_market_order,
    process_limit_order
)

router = APIRouter(prefix="/api/v1")
logger = logging.getLogger(__name__)

@router.post("/order", response_model=CreateOrderResponse, response_model_by_alias=False)
async def create_order(
    order: Union[LimitOrderBody, MarketOrderBody],
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Создание ордера (рыночного или лимитного)
    
    Parameters:
    - authorization: Токен авторизации в формате "TOKEN <token>"
    - Request Body:
        Для лимитного ордера:
        {
          "direction": "BUY" или "SELL",
          "ticker": "string",
          "qty": integer,
          "price": integer
        }
        
        Для рыночного ордера:
        {
          "direction": "BUY" или "SELL",
          "ticker": "string",
          "qty": integer
        }
    
    Responses:
    - 200: Успешный ответ
        {
          "success": true,
          "order_id": "string"
        }
    - 422: Ошибка валидации
    """
    # Проверка авторизации
    if not authorization or not authorization.startswith("TOKEN "):
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    api_key = authorization.split(" ")[1]
    
    # Получаем пользователя
    user = await get_user_by_token(db, api_key)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        if isinstance(order, LimitOrderBody):
            # Лимитный ордер
            result = await process_limit_order(db, order, authorization)
        else:
            # Рыночный ордер
            result = await process_market_order(db, order, str(user.id))
            
        return {"success": True, "id": str(result.id)}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Order creation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/orders")
async def get_user_orders(
    current_user: User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db)
):
    db_orders = await get_orders_by_user_id(db, str(current_user.id))
    out: List[Union[LimitOrder, MarketOrder]] = []
    for order in db_orders:
        if order.price is None:
            out.append(MarketOrder.model_validate(order))
        else:
            out.append(LimitOrder.model_validate(order))
    return out
