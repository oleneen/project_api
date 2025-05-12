from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from .. import schemas, models, crud
from ..database import get_db
from ..dependencies.auth import get_current_user

router = APIRouter()

@router.post("/instrument", response_model=schemas.Ok)
async def add_instrument(
    instrument: schemas.Instrument,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Требуются права администратора")
    
    db_instrument = await crud.get_instrument_by_ticker(db, instrument.ticker)
    if db_instrument:
        raise HTTPException(status_code=400, detail="Инструмент уже существует")
    
    await crud.create_instrument(db, instrument)
    
    return schemas.Ok(success=True)