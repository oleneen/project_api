from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import crud, schemas, models
from database import get_db
import uuid

router = APIRouter(prefix="/api/v1/public")

@router.post("/register", response_model=schemas.User)
def register(user: schemas.NewUser, db: Session = Depends(get_db)):
    api_key = f"key-{uuid.uuid4()}"
    db_user = models.User(name=user.name, api_key=api_key)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/instruments", response_model=List[schemas.Instrument])
def list_instruments(db: Session = Depends(get_db)):
    return crud.get_instruments(db)

@router.get("/orderbook/{ticker}", response_model=schemas.L2OrderBook)
def get_orderbook(ticker: str, limit: int = 10, db: Session = Depends(get_db)):
    # Логика формирования стакана
    pass