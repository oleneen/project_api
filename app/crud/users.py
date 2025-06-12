from sqlalchemy.exc import IntegrityError
from sqlalchemy import select,update
from sqlalchemy.ext.asyncio import AsyncSession
from .. import models
from ..schemas import NewUser,OrderStatus
from sqlalchemy import delete
from uuid import uuid4

async def get_user_by_token(db: AsyncSession, token: str):
    result = await db.execute(
        select(models.User).where(models.User.api_key == token)
    )
    return result.scalar_one_or_none()

async def register_user(db: AsyncSession, user_data: NewUser):
    api_key = f"key-{uuid4()}"
    user = models.User(name=user_data.name, api_key=api_key)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user



async def delete_user_all_data(user_id: str, db: AsyncSession) -> None:
    await db.execute(
        update(models.Order)
        .where(
            models.Order.user_id == user_id,
            models.Order.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED])  
        )
        .values(status=OrderStatus.CANCELLED)
    )


    await db.execute(
        delete(models.Balance).where(models.Balance.user_id == user_id)
    )