from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from ..crud.users import get_user_by_token
from ..database import get_db
from ..models import User  
from uuid import UUID

async def get_authenticated_user(
    authorization: str = Header(..., alias="Authorizations"),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not authorization.startswith("TOKEN "):
        raise HTTPException(401, "Неправильный формат токена")
    
    api_key = authorization[6:].strip()
    user = await get_user_by_token(db, api_key)
    
    if not user:
        raise HTTPException(401, "Токен не найден")
    return user

async def get_target_user_by_id_or_404(
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user

