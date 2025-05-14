
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app import models
from app.database import get_db

async def get_instrument_by_ticker_or_404(
    instrument_ticker: str,
    db: AsyncSession = Depends(get_db),
) -> models.Instrument:
    instrument = await db.get(models.Instrument, instrument_ticker)
    if not instrument:
        raise HTTPException(status_code=404, detail="Инструмент не найден")
    return instrument
