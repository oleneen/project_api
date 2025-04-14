from pydantic import BaseModel, UUID4
from typing import Optional, List
from enum import Enum

class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(str, Enum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"

class Balance(BaseModel):
    ticker: str
    amount: int

class OrderResponse(BaseModel):
    id: UUID4
    status: OrderStatus
    direction: Direction
    ticker: str
    qty: int
    price: Optional[int]
    filled: int
    created_at: datetime

class NewUser(BaseModel):
    name: str

class User(BaseModel):
    id: UUID4
    name: str
    api_key: str
    role: str

class Instrument(BaseModel):
    name: str
    ticker: str

class LimitOrderBody(BaseModel):
    direction: str  # "BUY" или "SELL"
    ticker: str
    qty: int
    price: int

class MarketOrderBody(BaseModel):
    direction: str
    ticker: str
    qty: int