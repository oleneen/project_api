from pydantic import BaseModel, UUID4, conint
from typing import Optional, List
from enum import Enum
from datetime import datetime
from decimal import Decimal

class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(str, Enum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"

class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"

class Balance(BaseModel):
    ticker: str
    amount: int

class OrderResponse(BaseModel):
    id: str
    direction: str
    instrument_ticker: str
    qty: int
    price: Optional[int]
    type: Optional[str]
    status: str
    created_at: str
    filled: int

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

class LimitOrderBody(BaseModel):
    direction: str  # "BUY" или "SELL"
    ticker: str
    qty: int
    price: int

class MarketOrderBody(BaseModel):
    direction: str
    ticker: str
    qty: int
    
class StatusResponse(BaseModel):
    status: str
    message: Optional[str] = None

# Схемы для операций с балансом
class DepositRequest(BaseModel):
    """Запрос на пополнение баланса"""
    user_id: UUID4
    ticker: str
    amount: conint(gt=0)  # Положительное число

class WithdrawRequest(BaseModel):
    """Запрос на списание средств"""
    user_id: UUID4
    ticker: str
    amount: conint(gt=0)  # Положительное число

class UpdateBalanceRequest(BaseModel):
    user_id: int  # ID пользователя, чей баланс нужно обновить
    operation: str  # Тип операции: "deposit" для пополнения или "withdraw" для списания
    amount: Decimal  # Сумма, на которую нужно изменить баланс

    class Config:
        from_attributes = True

class Ok(BaseModel):
    success: bool = True

#ниже правил:
class Level(BaseModel):
    price: int
    qty: int

class L2OrderBook(BaseModel):
    bids_levels: List[Level]  # Заявки на покупку (от высокой цены к низкой)
    ask_levels: List[Level]  # Заявки на продажу (от низкой цены к высокой)