from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from ..crud.users import get_user_by_token
from ..database import get_db
from ..models import User  

async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not authorization.startswith("TOKEN "):
        raise HTTPException(401, "Invalid token format")
    user = await get_user_by_token(db, authorization[6:])
    if not user:
        raise HTTPException(401, "Invalid token")
    return user