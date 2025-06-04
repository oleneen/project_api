from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SqlEnum
import enum
from .database import Base
import uuid
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    api_key = Column(String(100), unique=True, nullable=False)
    role = Column(String(10), nullable=False, server_default=text("USER"))
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

class Instrument(Base):
    __tablename__ = "instruments"
    ticker = Column(String(10), primary_key=True)
    name = Column(String)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

class Balance(Base):
    __tablename__ = "balances"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    instrument_ticker = Column(String, ForeignKey("instruments.ticker"), primary_key=True)
    amount = Column(Integer, default=0)
    locked = Column(Integer, default=0)
    user = relationship("User")

class OrderType(enum.Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"

class OrderDirection(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(enum.Enum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    CANCELLED = "CANCELLED"

class Order(Base):
    __tablename__ = "orders"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    direction = Column(SqlEnum(OrderDirection, name="order_direction_enum"), nullable=False)
    instrument_ticker = Column(String, ForeignKey("instruments.ticker"), nullable=False)
    qty = Column(Integer)
    price = Column(Integer, nullable=True)
    type = Column(SqlEnum(OrderType, name="order_type_enum"), nullable=False)
    status = Column(SqlEnum(OrderStatus, name="order_status_enum"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    filled = Column(Integer, default=0)

    user = relationship("User")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker = Column(String(10), nullable=False)
    qty = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    buy_order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    sell_order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
