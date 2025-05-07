from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from .. import crud
from ..schemas import Balance
from .. import models
from ..dependencies.auth import get_current_user

router = APIRouter()
@router.get("/balance", response_model=List[Balance])
async def get_user_balances(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    balances = await crud.get_user_balances(db, str(current_user.id))
    
    return [
        Balance(ticker=ticker, amount=amount)
        for ticker, amount in balances
    ]
