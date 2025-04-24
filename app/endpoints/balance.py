# /app/api/balance.py

from fastapi import APIRouter, HTTPException
from decimal import Decimal
from ..schemas import UpdateBalanceRequest, Ok, User

router = APIRouter()


@router.post("/api/v1/balance/update", response_model=Ok)
async def update_balance(data: UpdateBalanceRequest):
    user = await get_user_by_id(data.user_id)  # Получаем пользователя по ID

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.operation == "deposit":
        user.balance += data.amount
    elif data.operation == "withdraw":
        if user.balance < data.amount:
            raise HTTPException(status_code=400, detail="Insufficient funds")
        user.balance -= data.amount
    else:
        raise HTTPException(status_code=400, detail="Invalid operation type")

    await update_user_balance(user)  # Обновляем баланс в базе данных

    return Ok(message="Balance updated successfully", success=True)
