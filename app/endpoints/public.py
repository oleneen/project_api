from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from .. import crud 
from ..crud import get_instruments
from ..schemas import User as UserSchema, NewUser, Instrument
from ..models import User as UserModel
from ..database import get_db
from uuid import uuid4
from ..schemas import Level, L2OrderBook  
from ..crud import get_orderbook_data  
from fastapi.responses import JSONResponse
from fastapi import Query
import logging



router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/register", response_model=UserSchema)
async def register_user(request: NewUser, session: AsyncSession = Depends(get_db)):
    api_key = f"key-{uuid4()}"
    user = UserModel(name=request.name, api_key=api_key)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

@router.get("/instrument", response_model=List[Instrument])
async def list_instruments(db: AsyncSession = Depends(get_db)):
    try:
        instruments = await get_instruments(db)
        return instruments
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении списка инструментов: {str(e)}"
        )

@router.get("/orderbook/{ticker}", response_model=L2OrderBook)
async def get_orderbook(
    ticker: str,
    limit: int = Query(10, gt=0, le=25),  # Ограничения из OpenAPI
    db: AsyncSession = Depends(get_db)
):
    """
    Получение стакана заявок для указанного тикера.
    
    Responses:
        200: Успешный ответ со стаканом заявок
        404: Если инструмент не найден или нет активных заявок
        500: Ошибка сервера
    """
    try:
        orderbook = await crud.get_orderbook_data(db, ticker, limit)
        
        if orderbook is None:
            return JSONResponse(
                status_code=404,
                content={"detail": f"Нет активных заявок для инструмента {ticker}"}
            )
            
        return orderbook
        
    except ValueError as e:
        # Случай, когда инструмент не найден
        return JSONResponse(
            status_code=404,
            content={"detail": str(e)}
        )
    except Exception as e:
        logger.error(f"Orderbook error for {ticker}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера"
        )