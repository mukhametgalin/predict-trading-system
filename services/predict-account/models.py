"""SQLAlchemy models"""

from datetime import datetime
from sqlalchemy import Column, String, Boolean, Float, JSON, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import ARRAY

from database import Base


class Account(Base):
    """Predict.fun account"""
    __tablename__ = "predict_accounts"
    
    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    address = Column(String, nullable=False)  # Public address
    private_key = Column(String, nullable=False)  # Encrypted
    api_key = Column(String, nullable=True)  # Custom API key (optional)
    proxy_url = Column(String, nullable=True)  # HTTP/SOCKS5 proxy
    active = Column(Boolean, default=True)
    tags = Column(ARRAY(String), default=list)  # Tags for grouping
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Trade(Base):
    """Trade log"""
    __tablename__ = "predict_trades"
    
    id = Column(String, primary_key=True)
    account_id = Column(String, nullable=False)
    account_name = Column(String, nullable=False)
    market_id = Column(String, nullable=False)
    outcome_id = Column(String, nullable=False)
    side = Column(String, nullable=False)  # "yes" or "no"
    price = Column(Float, nullable=False)
    shares = Column(Float, nullable=False)
    order_hash = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, filled, cancelled, failed
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    filled_at = Column(DateTime, nullable=True)


class Position(Base):
    """Position tracking"""
    __tablename__ = "predict_positions"
    
    id = Column(String, primary_key=True)
    account_id = Column(String, nullable=False)
    market_id = Column(String, nullable=False)
    outcome_id = Column(String, nullable=False)
    side = Column(String, nullable=False)
    shares = Column(Float, nullable=False)
    avg_price = Column(Float, nullable=False)
    current_value = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
