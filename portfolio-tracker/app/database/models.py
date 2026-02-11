from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class TransactionType(enum.Enum):
    BUY = "buy"
    SELL = "sell"

class TaxClass(enum.Enum):
    CLASS_1 = "1"  # Single
    CLASS_2 = "2"  # Single parent
    CLASS_3 = "3"  # Married (higher earner)
    CLASS_4 = "4"  # Married (equal income)
    CLASS_5 = "5"  # Married (lower earner)
    CLASS_6 = "6"  # Second job

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Tax profile
    country = Column(String(50), default="Germany")
    tax_class = Column(Enum(TaxClass), default=TaxClass.CLASS_1)
    annual_income = Column(Float, default=0)  # Gross annual income
    is_married = Column(Boolean, default=False)
    has_church_tax = Column(Boolean, default=False)
    church_tax_rate = Column(Float, default=0.08)  # 8% or 9%
    used_allowance = Column(Float, default=0)  # Already used Sparerpauschbetrag this year
    
    portfolios = relationship("Portfolio", back_populates="user")

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="portfolios")
    transactions = relationship("Transaction", back_populates="portfolio")
    realized_pnls = relationship("RealizedPnL", back_populates="portfolio")

class Asset(Base):
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), unique=True, nullable=False)
    name = Column(String(100))
    asset_type = Column(String(20))
    sector = Column(String(50))
    country = Column(String(50))

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    symbol = Column(String(10), nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    fee = Column(Float, default=0)
    date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    portfolio = relationship("Portfolio", back_populates="transactions")
class RealizedPnL(Base):
    __tablename__ = "realized_pnl"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    symbol = Column(String, index=True)
    order_id = Column(String, unique=True, index=True)  # Trading212 order ID - tekrar kaydetmeyi önler
    realized_pnl = Column(Float)
    order_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    portfolio = relationship("Portfolio", back_populates="realized_pnls")