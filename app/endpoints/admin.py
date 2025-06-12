from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from .. import schemas, models, crud
from ..database import get_db
from ..dependencies.user import get_authenticated_user, get_target_user_by_id_or_404
from ..dependencies.instruments import get_instrument_by_ticker_or_404


router = APIRouter()

@router.post("/instrument", response_model=schemas.Ok)
async def add_instrument(
    instrument: schemas.Instrument,
    current_user: models.User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Требуются права администратора")
    
    db_instrument = await crud.get_instrument_by_ticker(db, instrument.ticker)
    if db_instrument:
        raise HTTPException(status_code=400, detail="Инструмент уже существует")

    await crud.create_instrument(db, instrument)
    
    return schemas.Ok(success=True)

@router.post("/balance/deposit", response_model=schemas.Ok)
async def deposit_balance(
    deposit: schemas.DepositRequest,
    current_user: models.User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Требуются права администратора")
    
    await get_target_user_by_id_or_404(deposit.user_id, db)
    await get_instrument_by_ticker_or_404(deposit.ticker, db)
    
    await crud.update_user_balance(
        db=db,
        user_id=deposit.user_id,
        ticker=deposit.ticker,
        amount=deposit.amount
    )

    return schemas.Ok(success=True)

@router.post("/balance/withdraw", response_model=schemas.Ok)
async def withdraw_from_balance(
    withdraw: schemas.WithdrawRequest,  
    current_user: models.User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Требуются права администратора")

    await get_target_user_by_id_or_404(withdraw.user_id, db)
    await get_instrument_by_ticker_or_404(withdraw.ticker, db)

    current_balance = await crud.get_available_balance(db, withdraw.user_id, withdraw.ticker)
    if current_balance < withdraw.amount:
        raise HTTPException(status_code=400, detail="Недостаточно средств на балансе")

    await crud.update_user_balance(
        db=db,
        user_id=withdraw.user_id,
        ticker=withdraw.ticker,
        amount=-withdraw.amount  
    )

    return schemas.Ok(success=True)


@router.delete("/instrument/{ticker}", response_model=schemas.Ok)
async def delete_instrument(
    ticker: str,
    current_user: models.User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Требуются права администратора")

    instrument = await get_instrument_by_ticker_or_404(ticker, db)
    await db.delete(instrument)
    await db.commit()

    return schemas.Ok(success=True)


@router.delete("/user/{user_id}", response_model=schemas.User)
async def delete_user(
    user: models.User = Depends(get_target_user_by_id_or_404),
    current_user: models.User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Требуются права администратора")

    await crud.delete_user_all_data(user.id, db)
    await db.delete(user)
    await db.commit()

    return user
