from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from .. import crud
from ..crud import get_instruments, get_transactions,get_instrument_by_ticker
from ..schemas import User as UserSchema, NewUser, Instrument, Transaction
from ..crud import register_user as register_user_crud
from ..database import get_db
from ..schemas import L2OrderBook
from fastapi.responses import JSONResponse
from fastapi import Query
import logging


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/register", response_model=UserSchema)
async def register_user(request: NewUser, db: AsyncSession = Depends(get_db)):
    return await register_user_crud(db, request)


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
    limit: int = Query(10, gt=0),
    db: AsyncSession = Depends(get_db)
):
    try:
        instrument = await get_instrument_by_ticker(db, ticker)
        if not instrument:
            raise HTTPException(status_code=404, detail="Инструмент не найден")
        
        orderbook = await crud.get_orderbook_data(db, ticker, limit)

        if orderbook is None:
            return JSONResponse(
                status_code=404,
                content={"detail": f"Нет активных заявок для инструмента {ticker}"}
            )

        return orderbook
    except HTTPException as e:
        raise e  # <-- пробрасываем как есть, не превращаем в 500
    except ValueError as e:
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


@router.get("/transactions/{ticker}", response_model=List[Transaction])
async def get_transactions_history(
    ticker: str,
    limit: int = Query(10, gt=0, le=25),
    db: AsyncSession = Depends(get_db)
):
    try:
        transactions = await get_transactions(db, ticker, limit)
        # Здесь мы пересчитываем amount вручную
        return [
            Transaction(
                ticker=t.ticker,
                amount=t.qty * t.price,  # <--- вот это ключевое
                price=t.price,
                timestamp=t.timestamp,
            )
            for t in transactions
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Ошибка при получении транзакций: {str(e)}")
