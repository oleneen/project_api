from pydantic import BaseModel, UUID4, Field
from typing import Optional, List, Union
from enum import Enum
from datetime import datetime

class OrderStatus(str, Enum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"

class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    
class OrderResponse(BaseModel):
    id: UUID4
    status: OrderStatus
    direction: Direction
    ticker: str
    qty: int
    price: Optional[int]
    filled: int
    created_at: datetime

class CreateOrderResponse(BaseModel):
    success: bool = Field(default=True)
    order_id: UUID4

class UserRole(Enum):
    USER = "USER"
    ADMIN = "ADMIN"

class MarketOrderBody(BaseModel):
    direction: Direction
    instrument_ticker: str
    qty: int

class MarketOrder(BaseModel):
    id: UUID4
    status: OrderStatus
    user_id: UUID4
    timestamp: datetime
    body: MarketOrderBody

class LimitOrderBody(BaseModel):
    direction: Direction
    instrument_ticker: str
    qty: int
    price: int

class LimitOrder(BaseModel):
    id: UUID4
    status: OrderStatus
    user_id: UUID4
    timestamp: datetime
    body: LimitOrderBody
    filled: int = 0

class NewUser(BaseModel):
    name: str

class User(BaseModel):
    id: UUID4
    name: str
    role: UserRole
    api_key: str

class Instrument(BaseModel):
    name: str
    ticker: str

# Схемы для операций с балансом
class DepositRequest(BaseModel):
    user_id: UUID4
    ticker: str
    amount: int = Field(..., gt=0)

class WithdrawRequest(BaseModel):
    user_id: UUID4
    ticker: str
    amount: int = Field(..., gt=0)

class Transaction(BaseModel):
    ticker: str
    amount: int
    price: int
    timestamp: datetime

class Ok(BaseModel):
    success: bool = True

class Level(BaseModel):
    price: int
    qty: int

class L2OrderBook(BaseModel):
    bids_levels: List[Level]  # Заявки на покупку (от высокой цены к низкой)
    ask_levels: List[Level]  # Заявки на продажу (от низкой цены к высокой)

class ValidationError:
    loc: List[Union[str, int]]
    msg: str
    type: str

class HTTPValidationError:
    detail: List[ValidationError]