from pydantic import BaseModel, UUID4, StrictInt, Field, model_validator
from typing import Any, Dict, List, Union
from enum import Enum
from datetime import datetime

class OrderStatus(str, Enum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    CANCELLED = "CANCELLED"

class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class CreateOrderResponse(BaseModel):
    success: bool = Field(default=True)
    order_id: UUID4
    
class UserRole(Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class LimitOrderBody(BaseModel):
    direction: Direction
    ticker: str
    qty: int = Field(..., gt=0)
    price: int

    class Config:
        from_attributes = True


class MarketOrderBody(BaseModel):
    direction: Direction
    ticker: str
    qty: int = Field(..., gt=0)

    model_config = {
        'from_attributes': True,
        'extra': 'forbid'
    }


class LimitOrder(BaseModel):
    id: UUID4
    status: OrderStatus
    user_id: UUID4
    timestamp: datetime
    body: LimitOrderBody
    filled: int = 0

    @model_validator(mode="before")
    def assemble_body(cls, values):
        if not isinstance(values, dict):
            order = values
            values = {
                "id": order.id,
                "status": order.status,
                "user_id": order.user_id,
                "timestamp": order.timestamp,
                "filled": order.filled,
                "direction": order.direction,
                "instrument_ticker": order.instrument_ticker,
                "qty": order.qty,
                "price": order.price,
            }
        return {
            **values,
            "body": {
                "direction": values["direction"],
                "ticker": values["instrument_ticker"],
                "qty": values["qty"],
                "price": values["price"],
            },
        }

    class Config:
        from_attributes = True
        validate_by_name = True


class MarketOrder(BaseModel):
    id: UUID4
    status: OrderStatus
    user_id: UUID4
    timestamp: datetime
    body: MarketOrderBody

    @model_validator(mode="before")
    def assemble_body(cls, values):
        if not isinstance(values, dict):
            order = values
            values = {
                "id": order.id,
                "status": order.status,
                "user_id": order.user_id,
                "timestamp": order.timestamp,
                "direction": order.direction,
                "instrument_ticker": order.instrument_ticker,
                "qty": order.qty,
            }
        return {
            **values,
            "body": {
                "direction": values["direction"],
                "ticker": values["instrument_ticker"],
                "qty": values["qty"],
            },
        }

    class Config:
        from_attributes = True
        validate_by_name = True

class NewUser(BaseModel):
    name: str = Field(..., min_length=3)

class User(BaseModel):
    id: UUID4
    name: str
    role: UserRole
    api_key: str

    class Config:
        orm_mode = True

class Instrument(BaseModel):
    name: str
    ticker: str = Field(..., min_length=2, max_length=10, pattern="^[A-Z]{2,10}$")

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

    class Config:
        orm_mode = True

class Ok(BaseModel):
    success: bool = True

class Level(BaseModel):
    price: int
    qty: int

class L2OrderBook(BaseModel):
    bid_levels: List[Level]  
    ask_levels: List[Level] 

class ValidationError:
    loc: List[Union[str, int]]
    msg: str
    type: str

class HTTPValidationError:
    detail: List[ValidationError]

#Схемы для формирования отчетов
class ReportRequest(BaseModel):
    year: int = Field(..., ge=2020, le=2100)
    month: int = Field(..., ge=1, le=12)
    
class ReportInfo(BaseModel):
    id: UUID4
    user_id: UUID4
    year: int
    month: int
    file_url: str
    generated_at: datetime
    trade_count: int = Field(default=0) 
    status: str = Field(default="completed")
    
    class Config:
        from_attributes = True