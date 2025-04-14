from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func  # Добавьте эту строку
from sqlalchemy.orm import relationship
from .database import Base
import uuid

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    api_key = Column(String, unique=True)
    role = Column(String, default="USER")

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
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    direction = Column(String)  # BUY/SELL
    ticker = Column(String)
    qty = Column(Integer)
    price = Column(Integer, nullable=True)  # null для рыночных ордеров
    status = Column(String, default="NEW")  # NEW, EXECUTED, CANCELLED
    created_at = Column(DateTime, server_default=func.now())
    filled = Column(Integer, default=0)
    user = relationship("User")