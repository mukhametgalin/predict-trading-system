"""
Predict.fun Account Service
Manages accounts, executes trades, monitors fills
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from models import Account, Trade, Position
from database import get_db, init_db
from schemas import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    TradeRequest,
    TradeResponse,
    TradeSummary,
    PositionResponse,
)
from predict_client import PredictClient
from event_publisher import EventPublisher

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global clients
predict_client: PredictClient = None
event_publisher: EventPublisher = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global predict_client, event_publisher
    
    # Startup
    logger.info("Starting Predict Account Service...")
    await init_db()
    
    predict_client = PredictClient(
        api_key=os.getenv("PREDICT_API_KEY"),
        base_url=os.getenv("PREDICT_API_URL", "https://api.predict.fun"),
    )
    
    event_publisher = EventPublisher(
        redis_host=os.getenv("REDIS_HOST", "redis"),
        redis_port=int(os.getenv("REDIS_PORT", 6379)),
    )
    
    logger.info("Predict Account Service started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Predict Account Service...")
    await event_publisher.close()


app = FastAPI(
    title="Predict Account Service",
    description="Account management and trading for Predict.fun",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Health =====

@app.get("/")
async def root():
    return {"status": "ok", "service": "predict-account"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


# ===== Accounts =====

@app.post("/accounts", response_model=AccountResponse)
async def create_account(
    account_data: AccountCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create new account"""
    from crud import create_account as db_create_account
    
    account = await db_create_account(db, account_data)
    
    # Publish event
    await event_publisher.publish_account_event("account_created", {
        "account_id": account.id,
        "name": account.name,
        "platform": "predict",
    })
    
    return account


@app.get("/accounts", response_model=list[AccountResponse])
async def list_accounts(
    active_only: bool = False,
    tag: str = None,
    db: AsyncSession = Depends(get_db),
):
    """List all accounts"""
    from crud import get_accounts
    
    accounts = await get_accounts(db, active_only=active_only, tag=tag)
    return accounts


@app.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get account by ID"""
    from crud import get_account
    
    account = await get_account(db, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return account


@app.put("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: str,
    account_data: AccountUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update account"""
    from crud import update_account as db_update_account
    
    account = await db_update_account(db, account_id, account_data)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Publish event
    await event_publisher.publish_account_event("account_updated", {
        "account_id": account.id,
        "name": account.name,
        "active": account.active,
        "tags": account.tags,
    })
    
    return account


@app.delete("/accounts/{account_id}")
async def delete_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete account"""
    from crud import delete_account as db_delete_account
    
    success = await db_delete_account(db, account_id)
    if not success:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Publish event
    await event_publisher.publish_account_event("account_deleted", {
        "account_id": account_id,
    })
    
    return {"status": "deleted"}


# ===== Trading =====

@app.get("/trades", response_model=list[TradeSummary])
async def list_trades(
    account_id: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List recent trades"""
    from crud import get_trades

    limit = max(1, min(limit, 200))
    trades = await get_trades(db, account_id=account_id, limit=limit)
    return trades


@app.post("/trade", response_model=TradeResponse)
async def execute_trade(
    trade_request: TradeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Execute trade on Predict.fun"""
    from crud import get_account
    from trade_executor import execute_trade
    
    # Get account
    account = await get_account(db, trade_request.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if not account.active:
        raise HTTPException(status_code=400, detail="Account is inactive")
    
    # Execute trade
    try:
        result = await execute_trade(
            predict_client=predict_client,
            account=account,
            trade_request=trade_request,
        )

        # Persist trade (so UI can display history even for dry-run)
        from crud import create_trade as db_create_trade

        trade_row = await db_create_trade(
            db,
            account_id=account.id,
            account_name=account.name,
            market_id=trade_request.market_id,
            outcome_id=result.get("outcome_id") or "",
            side=trade_request.side,
            price=trade_request.price,
            shares=trade_request.shares,
            order_hash=result.get("order_hash"),
        )
        # Reflect status on the DB row
        if result.get("status") == "dry_run":
            trade_row.status = "dry_run"
        else:
            trade_row.status = result.get("status") or "submitted"
        await db.commit()

        # Publish event (avoid emitting "executed" on dry-run)
        if result.get("status") == "dry_run":
            await event_publisher.publish_trade_event(
                "trade_dry_run",
                {
                    "account_id": account.id,
                    "account_name": account.name,
                    "market_id": trade_request.market_id,
                    "side": trade_request.side,
                    "price": trade_request.price,
                    "shares": trade_request.shares,
                    "platform": "predict",
                },
            )
        else:
            await event_publisher.publish_trade_event(
                "trade_executed",
                {
                    "account_id": account.id,
                    "account_name": account.name,
                    "market_id": trade_request.market_id,
                    "side": trade_request.side,
                    "price": trade_request.price,
                    "shares": trade_request.shares,
                    "order_hash": result.get("order_hash"),
                    "platform": "predict",
                },
            )

        return result
        
    except Exception as e:
        import traceback
        err_text = str(e) or repr(e)
        logger.error(f"Trade execution failed: {err_text}")
        logger.error(traceback.format_exc())
        
        # Publish error event
        await event_publisher.publish_trade_event("trade_error", {
            "account_id": account.id,
            "account_name": account.name,
            "market_id": trade_request.market_id,
            "error": err_text,
            "platform": "predict",
        })
        
        raise HTTPException(status_code=500, detail=err_text)


@app.get("/positions/{account_id}", response_model=list[PositionResponse])
async def get_positions(
    account_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get account positions"""
    from crud import get_account
    
    account = await get_account(db, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Get positions from Predict.fun API
    try:
        positions = await predict_client.get_positions(account.address)
        return positions
    except Exception as e:
        logger.error(f"Failed to get positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== WebSocket for fills monitoring =====

@app.websocket("/ws/fills")
async def websocket_fills(websocket):
    """WebSocket endpoint for monitoring fills"""
    await websocket.accept()
    
    # TODO: Implement WebSocket fill monitoring
    # This will listen to Predict.fun WebSocket and forward fill events
    
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages
            pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
