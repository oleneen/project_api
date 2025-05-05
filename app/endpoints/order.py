from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from ..database import get_db
from ..models import Order, User
from pydantic import BaseModel
from ..schemas import OrderResponse

router = APIRouter()

@router.get("/orders", response_model=List[OrderResponse])
async def get_user_orders(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    # Проверка авторизации
    if not authorization or not authorization.startswith("TOKEN "):
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    api_key = authorization.split(" ")[1]
    # TODO:у нас есть в admin.py есть чудесная функция получения пользователя по токену, давайте пользоваться ей
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