from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from ..database import get_db
from ..models import Order, User
from ..schemas import OrderResponse
from ..dependencies.auth import get_current_user  

router = APIRouter()

@router.get("/orders", response_model=List[OrderResponse])
async def get_user_orders(
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):

    result = await db.execute(
        select(Order).where(Order.user_id == str(current_user.id))
    )
    orders = result.scalars().all()
    
    return orders
