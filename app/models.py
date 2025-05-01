from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func  # Добавьте эту строку
from sqlalchemy.orm import relationship
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
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

class Instrument(Base):
    __tablename__ = "instruments"
    ticker = Column(String(10), primary_key=True)
    name = Column(String)

class Balance(Base):
    __tablename__ = "balances"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    ticker = Column(String)
    amount = Column(Integer, default=0)
    user = relationship("User")

class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    direction = Column(String)  # BUY/SELL
    instrument_ticker = Column(String)  # Было ticker, стало instrument_ticker
    qty = Column(Integer)
    price = Column(Integer, nullable=True)
    type = Column(String)  # Дополнительное поле (если нужно)
    status = Column(String)  # Оставляем, если status есть в БД
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    filled = Column(Integer, default=0)
    
    user = relationship("User")