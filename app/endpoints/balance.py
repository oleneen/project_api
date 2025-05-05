from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from .. import crud
from ..schemas import Balance

router = APIRouter()
@router.get("/balance", response_model=List[Balance])
async def get_balances(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    # Проверяем наличие токена авторизации
    if not authorization or not authorization.startswith("TOKEN "):
        raise HTTPException(status_code=401, detail="Authorization token is missing or invalid")
    
    api_key = authorization.split(" ")[1]
    
    # Получаем пользователя по токену
    user = await crud.get_user_by_token(db, api_key)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    balances = await crud.get_user_balances(db, str(user.id))
    
    # Если у пользователя нет балансов, возвращаем пустой словарь
    if not balances:
        return {}
    
    # Форматируем ответ в виде словаря {ticker: amount}
    balance_dict = {ticker: amount for (ticker, amount) in balances}
    
    return balance_dict

# @router.post("/api/v1/balance/update", response_model=Ok)
# async def update_balance(data: UpdateBalanceRequest):
#     user = await get_user_by_id(data.user_id)  # Получаем пользователя по ID

#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")

#     if data.operation == "deposit":
#         user.balance += data.amount
#     elif data.operation == "withdraw":
#         if user.balance < data.amount:
#             raise HTTPException(status_code=400, detail="Insufficient funds")
#         user.balance -= data.amount
#     else:
#         raise HTTPException(status_code=400, detail="Invalid operation type")

#     await update_user_balance(user)  # Обновляем баланс в базе данных

#     return Ok(message="Balance updated successfully", success=True)
