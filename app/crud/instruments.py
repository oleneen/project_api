from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .. import models, schemas

async def create_instrument(db: AsyncSession, instrument: schemas.Instrument):
    db_instrument = models.Instrument(**instrument.dict())
    db.add(db_instrument)
    await db.commit()
    await db.refresh(db_instrument)
    return db_instrument

async def get_instruments(db: AsyncSession):
    result = await db.execute(select(models.Instrument))
    return result.scalars().all()

async def get_instrument_by_ticker(db: AsyncSession, ticker: str):
    result = await db.execute(
        select(models.Instrument).where(models.Instrument.ticker == ticker)
    )
    return result.scalar_one_or_none()