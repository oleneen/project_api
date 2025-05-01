# /app/endpoints/order.py
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from ..database import get_db
from ..models import Order, User
from pydantic import BaseModel

router = APIRouter()

# Модель для ответа
class OrderResponse(BaseModel):
    id: str
    direction: str
    instrument_ticker: str
    qty: int
    price: Optional[int]
    type: Optional[str]
    status: str
    created_at: str
    filled: int

    class Config:
        from_attributes = True

@router.get("/orders", response_model=List[OrderResponse])
async def get_user_orders(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    # Проверка авторизации
    if not authorization or not authorization.startswith("TOKEN "):
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    api_key = authorization.split(" ")[1]
    
    # Получаем пользователя
    user = await db.execute(
        select(User).where(User.api_key == api_key)
    )
    user = user.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Получаем ордера пользователя
    result = await db.execute(
        select(Order).where(Order.user_id == str(user.id))
    )
    orders = result.scalars().all()
    
    return orders