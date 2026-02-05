"""Pydantic schemas for Web API"""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


# ===== Dashboard =====

class DashboardStats(BaseModel):
    total_accounts: int
    active_accounts: int
    total_trades_24h: int
    total_pnl_24h: float
    active_strategies: int
    pending_alerts: int


class AccountSummary(BaseModel):
    id: str
    name: str
    platform: str
    address: str
    active: bool
    balance: Optional[float] = None
    positions_count: int = 0
    pnl_24h: float = 0


class MarketSummary(BaseModel):
    market_id: str
    platform: str
    question: str
    category: str
    yes_price: float
    no_price: float
    volume_24h: float
    liquidity: float


# ===== Accounts =====

class AccountCreate(BaseModel):
    platform: str = "predict"
    name: str
    private_key: str
    api_key: Optional[str] = None
    proxy_url: Optional[str] = None
    tags: list[str] = []
    notes: Optional[str] = None


class AccountUpdate(BaseModel):
    active: Optional[bool] = None
    tags: Optional[list[str]] = None
    notes: Optional[str] = None
    proxy_url: Optional[str] = None


class AccountDetail(BaseModel):
    id: str
    platform: str
    name: str
    address: str
    active: bool
    tags: list[str]
    notes: Optional[str]
    created_at: datetime
    positions: list[dict] = []
    recent_trades: list[dict] = []


# ===== Trading =====

class TradeRequest(BaseModel):
    account_id: str
    market_id: str
    side: str = Field(..., pattern="^(yes|no)$")
    price: float = Field(..., gt=0, le=1)
    shares: float = Field(..., gt=0)
    confirm: bool = False


class TradeResponse(BaseModel):
    trade_id: str
    status: str
    message: str
    order_hash: Optional[str] = None


# ===== Strategies =====

class StrategyCreate(BaseModel):
    name: str
    type: str  # delta_neutral, arbitrage, market_maker
    config: dict = {}
    enabled: bool = False


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[dict] = None
    enabled: Optional[bool] = None


class StrategyDetail(BaseModel):
    id: str
    name: str
    type: str
    config: dict
    enabled: bool
    created_at: datetime
    recent_logs: list[dict] = []


# ===== Alerts =====

class AlertResponse(BaseModel):
    id: str
    type: str
    title: str
    message: Optional[str]
    data: Optional[dict]
    read: bool
    created_at: datetime


# ===== WebSocket =====

class WSMessage(BaseModel):
    type: str  # trade, fill, alert, price
    data: Any
    timestamp: datetime = Field(default_factory=datetime.utcnow)
