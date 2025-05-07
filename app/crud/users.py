from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .. import models

async def get_user_by_token(db: AsyncSession, token: str):
    result = await db.execute(
        select(models.User).where(models.User.api_key == token)
    )
    return result.scalar_one_or_none()