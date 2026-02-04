"""Pydantic schemas"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ===== Account Schemas =====

class AccountCreate(BaseModel):
    name: str
    private_key: str
    proxy_url: Optional[str] = None
    api_key: Optional[str] = None
    tags: list[str] = []
    notes: Optional[str] = None


class AccountUpdate(BaseModel):
    active: Optional[bool] = None
    tags: Optional[list[str]] = None
    notes: Optional[str] = None
    proxy_url: Optional[str] = None


class AccountResponse(BaseModel):
    id: str
    name: str
    address: str
    active: bool
    tags: list[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ===== Trade Schemas =====

class TradeRequest(BaseModel):
    account_id: str
    market_id: str
    side: str = Field(..., pattern="^(yes|no)$")
    price: float = Field(..., gt=0, le=1)
    shares: float = Field(..., gt=0)
    confirm: bool = False  # Dry-run protection


class TradeResponse(BaseModel):
    trade_id: str
    account_id: str
    account_name: str
    market_id: str
    side: str
    price: float
    shares: float
    order_hash: Optional[str] = None
    status: str
    message: str


# ===== Position Schemas =====

class PositionResponse(BaseModel):
    account_id: str
    market_id: str
    outcome_id: str
    side: str
    shares: float
    avg_price: float
    current_value: Optional[float] = None
    pnl: Optional[float] = None
