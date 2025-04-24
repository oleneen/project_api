from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..crud import get_instruments
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from ..schemas import User as UserSchema, NewUser, Instrument
from ..models import User as UserModel
from ..database import get_db
from uuid import uuid4

router = APIRouter()

@router.post("/register", response_model=UserSchema)
async def register_user(request: NewUser, session: AsyncSession = Depends(get_db)):
    api_key = f"key-{uuid4()}"
    user = UserModel(name=request.name, api_key=api_key)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

@router.get("/instruments", response_model=List[Instrument])
def list_instruments(db: Session = Depends(get_db)):
    return get_instruments(db)

# @router.get("/orderbook/{ticker}", response_model=L2OrderBook)
# def get_orderbook(ticker: str, limit: int = 10, db: Session = Depends(get_db)):
#     # Логика формирования стакана
#     pass