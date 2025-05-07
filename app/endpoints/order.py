from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..database import get_db
from ..models import User
from ..schemas import OrderResponse
from ..dependencies.auth import get_current_user
from ..crud import get_orders_by_user_id

router = APIRouter()

@router.get("/orders", response_model=List[OrderResponse])
async def get_user_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await get_orders_by_user_id(db, str(current_user.id))
