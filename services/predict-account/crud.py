"""CRUD operations for database"""

import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from eth_account import Account as EthAccount

from models import Account, Trade, Position
from schemas import AccountCreate, AccountUpdate


# ===== Accounts =====

async def create_account(db: AsyncSession, account_data: AccountCreate) -> Account:
    """Create new account"""
    # Derive address from private key
    eth_account = EthAccount.from_key(account_data.private_key)
    
    account = Account(
        id=str(uuid.uuid4()),
        name=account_data.name,
        address=eth_account.address,
        private_key=account_data.private_key,  # TODO: Encrypt
        api_key=account_data.api_key,
        proxy_url=account_data.proxy_url,
        tags=account_data.tags,
        notes=account_data.notes,
    )
    
    db.add(account)
    await db.flush()
    
    return account


async def get_account(db: AsyncSession, account_id: str) -> Optional[Account]:
    """Get account by ID"""
    result = await db.execute(
        select(Account).where(Account.id == account_id)
    )
    return result.scalar_one_or_none()


async def get_account_by_name(db: AsyncSession, name: str) -> Optional[Account]:
    """Get account by name"""
    result = await db.execute(
        select(Account).where(Account.name == name)
    )
    return result.scalar_one_or_none()


async def get_accounts(
    db: AsyncSession,
    active_only: bool = False,
    tag: Optional[str] = None,
) -> list[Account]:
    """Get all accounts with filters"""
    query = select(Account)
    
    if active_only:
        query = query.where(Account.active == True)
    
    if tag:
        query = query.where(Account.tags.contains([tag]))
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_account(
    db: AsyncSession,
    account_id: str,
    account_data: AccountUpdate,
) -> Optional[Account]:
    """Update account"""
    account = await get_account(db, account_id)
    if not account:
        return None
    
    if account_data.active is not None:
        account.active = account_data.active
    if account_data.tags is not None:
        account.tags = account_data.tags
    if account_data.notes is not None:
        account.notes = account_data.notes
    if account_data.proxy_url is not None:
        account.proxy_url = account_data.proxy_url
    
    await db.flush()
    return account


async def delete_account(db: AsyncSession, account_id: str) -> bool:
    """Delete account"""
    account = await get_account(db, account_id)
    if not account:
        return False
    
    await db.delete(account)
    await db.flush()
    return True


# ===== Trades =====

async def get_trades(
    db: AsyncSession,
    account_id: Optional[str] = None,
    limit: int = 50,
) -> list[Trade]:
    """List recent trades (optionally filtered by account_id)"""
    query = select(Trade).order_by(Trade.created_at.desc()).limit(limit)
    if account_id:
        query = query.where(Trade.account_id == account_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_trade(
    db: AsyncSession,
    account_id: str,
    account_name: str,
    market_id: str,
    outcome_id: str,
    side: str,
    price: float,
    shares: float,
    order_hash: Optional[str] = None,
) -> Trade:
    """Create trade record"""
    trade = Trade(
        id=str(uuid.uuid4()),
        account_id=account_id,
        account_name=account_name,
        market_id=market_id,
        outcome_id=outcome_id,
        side=side,
        price=price,
        shares=shares,
        order_hash=order_hash,
        status="pending",
    )
    
    db.add(trade)
    await db.flush()
    return trade


async def update_trade_status(
    db: AsyncSession,
    trade_id: str,
    status: str,
    error: Optional[str] = None,
) -> Optional[Trade]:
    """Update trade status"""
    result = await db.execute(
        select(Trade).where(Trade.id == trade_id)
    )
    trade = result.scalar_one_or_none()
    
    if not trade:
        return None
    
    trade.status = status
    if error:
        trade.error = error
    
    await db.flush()
    return trade
