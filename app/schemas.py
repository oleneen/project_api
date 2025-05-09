from pydantic import BaseModel, UUID4, Field
from typing import Optional, List, Union, Literal
from enum import Enum
from datetime import datetime
from decimal import Decimal

class Balance(BaseModel):
    user_id: int
    amount: float
    currency: str = "USD"  # Пример значения по умолчанию

    class Config:
        from_attributes = True  # Для совместимости с ORM (ранее orm_mode=True)

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

class Direction(Enum):
    BUY = 0
    SELL = 1

class OrderStatus(Enum):
    NEW = 0
    EXECUTED = 1
    PARTIALLY_EXECUTED = 2
    CANCELLED = 3

class UserRole(Enum):
    USER = 0
    ADMIN = 1

class MarketOrderBody(BaseModel):
    direction: Literal["BUY", "SELL"]
    instrument_ticker: str
    qty: int
    type: Literal["MARKET"] = "MARKET"
class MarketOrder(BaseModel):
    id: UUID4
    status: OrderStatus
    user_id: UUID4
    timestamp: datetime
    body: MarketOrderBody

class LimitOrderBody(BaseModel):
    direction: Literal["BUY", "SELL"]
    instrument_ticker: str
    qty: int
    price: int  # Основное отличие от рыночного ордера
    type: Literal["LIMIT"] = "LIMIT"  # Тип ордера

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

#TODO: убираем? в свагере этого нет
class StatusResponse(BaseModel):
    status: str
    message: Optional[str] = None

# Схемы для операций с балансом
class DepositRequest(BaseModel):
    user_id: UUID4
    ticker: str
    amount: int = Field(..., gt=0)

class WithdrawRequest(BaseModel):
    user_id: UUID4
    ticker: str
    amount: int = Field(..., gt=0)

#TODO: это точно нужно здесь?
class UpdateBalanceRequest(BaseModel):
    user_id: int  # ID пользователя, чей баланс нужно обновить
    operation: str  # Тип операции: "deposit" для пополнения или "withdraw" для списания
    amount: Decimal  # Сумма, на которую нужно изменить баланс

    class Config:
        from_attributes = True

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