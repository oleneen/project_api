from fastapi import APIRouter, Depends
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from .. import crud
from .. import models
from ..dependencies.user import get_authenticated_user

router = APIRouter()
@router.get("/balance", response_model=Dict[str, int])
async def get_user_balances(
    current_user: models.User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db)
):
    balances = await crud.get_user_balances(db, str(current_user.id))

    return {ticker: amount for ticker, amount in balances}