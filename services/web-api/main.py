"""
Web API Gateway
Central API for UI and external integrations
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

import httpx

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db, get_clickhouse
from schemas import (
    DashboardStats,
    AccountSummary,
    AccountCreate,
    AccountUpdate,
    AccountDetail,
    TradeRequest,
    TradeResponse,
    StrategyCreate,
    StrategyUpdate,
    StrategyDetail,
    AlertResponse,
    MarketSummary,
)
from services import predict_service, polymarket_service, strategy_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WebSocket connections
ws_connections: set[WebSocket] = set()

# Redis for events
redis_client: redis.Redis = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown"""
    global redis_client
    
    logger.info("Starting Web API Gateway...")
    
    # Connect to Redis
    redis_client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        decode_responses=True,
    )
    
    # Start event listener
    asyncio.create_task(event_listener())
    
    logger.info("Web API Gateway started")
    yield
    
    # Shutdown
    logger.info("Shutting down Web API Gateway...")
    await redis_client.close()


app = FastAPI(
    title="Predict Trading System API",
    description="Central API Gateway for trading system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Event Listener =====

async def event_listener():
    """Listen to Redis streams and broadcast to WebSocket clients"""
    streams = ["trade_events", "fill_events", "account_events"]
    last_ids = {s: "0" for s in streams}
    
    while True:
        try:
            # Read from multiple streams
            results = await redis_client.xread(
                {s: last_ids[s] for s in streams},
                count=100,
                block=1000,
            )
            
            for stream, messages in results:
                for msg_id, data in messages:
                    last_ids[stream] = msg_id
                    
                    # Broadcast to WebSocket clients
                    await broadcast_ws({
                        "type": stream,
                        "data": data,
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                    
        except Exception as e:
            logger.error(f"Event listener error: {e}")
            await asyncio.sleep(1)


async def broadcast_ws(message: dict):
    """Broadcast message to all WebSocket connections"""
    if not ws_connections:
        return
    
    data = json.dumps(message)
    dead = set()
    
    for ws in ws_connections:
        try:
            await ws.send_text(data)
        except Exception:
            dead.add(ws)
    
    ws_connections.difference_update(dead)


# ===== Health =====

@app.get("/")
async def root():
    return {"status": "ok", "service": "web-api"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


# ===== Dashboard =====

@app.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get dashboard statistics"""
    # Get account counts
    result = await db.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE active = true) as active
        FROM accounts
    """))
    row = result.fetchone()
    total_accounts = row[0] if row else 0
    active_accounts = row[1] if row else 0
    
    # Get trades in last 24h
    result = await db.execute(text("""
        SELECT COUNT(*), COALESCE(SUM(price * shares), 0)
        FROM trades
        WHERE created_at > NOW() - INTERVAL '24 hours'
    """))
    row = result.fetchone()
    total_trades_24h = row[0] if row else 0
    # PnL calculation is simplified - would need proper logic
    total_pnl_24h = 0.0
    
    # Get active strategies
    result = await db.execute(text("""
        SELECT COUNT(*) FROM strategies WHERE enabled = true
    """))
    row = result.fetchone()
    active_strategies = row[0] if row else 0
    
    # Get unread alerts
    result = await db.execute(text("""
        SELECT COUNT(*) FROM alerts WHERE read = false
    """))
    row = result.fetchone()
    pending_alerts = row[0] if row else 0
    
    return DashboardStats(
        total_accounts=total_accounts,
        active_accounts=active_accounts,
        total_trades_24h=total_trades_24h,
        total_pnl_24h=total_pnl_24h,
        active_strategies=active_strategies,
        pending_alerts=pending_alerts,
    )


# ===== Accounts =====

@app.get("/accounts", response_model=list[AccountSummary])
async def list_accounts(
    platform: Optional[str] = None,
    active_only: bool = False,
    tag: Optional[str] = None,
):
    """List all accounts across platforms"""
    accounts = []
    
    # Get Predict accounts
    if platform is None or platform == "predict":
        try:
            predict_accounts = await predict_service.list_accounts(active_only, tag)
            for acc in predict_accounts:
                accounts.append(AccountSummary(
                    id=acc["id"],
                    name=acc["name"],
                    platform="predict",
                    address=acc["address"],
                    active=acc["active"],
                ))
        except Exception as e:
            logger.warning(f"Failed to get predict accounts: {e}")
    
    # Get Polymarket accounts
    if platform is None or platform == "polymarket":
        try:
            poly_accounts = await polymarket_service.list_accounts(active_only, tag)
            for acc in poly_accounts:
                accounts.append(AccountSummary(
                    id=acc["id"],
                    name=acc["name"],
                    platform="polymarket",
                    address=acc["address"],
                    active=acc["active"],
                ))
        except Exception as e:
            logger.warning(f"Failed to get polymarket accounts: {e}")
    
    return accounts


@app.post("/accounts", response_model=AccountSummary)
async def create_account(data: AccountCreate):
    """Create new account"""
    if data.platform == "predict":
        result = await predict_service.create_account(data.model_dump())
    elif data.platform == "polymarket":
        result = await polymarket_service.create_account(data.model_dump())
    else:
        raise HTTPException(400, f"Unknown platform: {data.platform}")
    
    return AccountSummary(
        id=result["id"],
        name=result["name"],
        platform=data.platform,
        address=result["address"],
        active=result["active"],
    )


@app.get("/accounts/{platform}/{account_id}", response_model=AccountDetail)
async def get_account(platform: str, account_id: str):
    """Get account details"""
    if platform == "predict":
        account = await predict_service.get_account(account_id)
        positions = await predict_service.get_positions(account_id)
    elif platform == "polymarket":
        account = await polymarket_service.get_account(account_id)
        positions = await polymarket_service.get_positions(account_id)
    else:
        raise HTTPException(400, f"Unknown platform: {platform}")
    
    return AccountDetail(
        id=account["id"],
        platform=platform,
        name=account["name"],
        address=account["address"],
        active=account["active"],
        tags=account.get("tags", []),
        notes=account.get("notes"),
        created_at=account["created_at"],
        positions=positions,
    )


@app.put("/accounts/{platform}/{account_id}", response_model=AccountSummary)
async def update_account(platform: str, account_id: str, data: AccountUpdate):
    """Update account"""
    update_data = data.model_dump(exclude_none=True)
    
    if platform == "predict":
        result = await predict_service.update_account(account_id, update_data)
    elif platform == "polymarket":
        result = await polymarket_service.update_account(account_id, update_data)
    else:
        raise HTTPException(400, f"Unknown platform: {platform}")
    
    return AccountSummary(
        id=result["id"],
        name=result["name"],
        platform=platform,
        address=result["address"],
        active=result["active"],
    )


@app.post("/accounts/{platform}/{account_id}/disable", response_model=AccountSummary)
async def disable_account(
    platform: str,
    account_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Disable trading on account and remove it from strategies.

    Note: exchange-side cancellation/position close is NOT implemented yet.
    This endpoint is the system-level kill-switch.
    """

    # 1) Disable account (kill-switch)
    if platform == "predict":
        result = await predict_service.update_account(account_id, {"active": False})
    elif platform == "polymarket":
        result = await polymarket_service.update_account(account_id, {"active": False})
    else:
        raise HTTPException(400, f"Unknown platform: {platform}")

    # 2) Remove from strategies configs
    strategies = await db.execute(text("SELECT id, config FROM strategies"))
    changed = 0

    for row in strategies.fetchall():
        sid = str(row[0])
        config = row[1] or {}
        new_config = dict(config)
        did_change = False

        # Generic strategy membership list
        if isinstance(new_config.get("account_ids"), list):
            before = list(new_config["account_ids"])
            after = [x for x in before if x != account_id]
            if after != before:
                new_config["account_ids"] = after
                did_change = True

        # Delta-neutral config (pairs of accounts)
        if isinstance(new_config.get("pairs"), list):
            before_pairs = list(new_config["pairs"])
            after_pairs = [
                p
                for p in before_pairs
                if isinstance(p, dict)
                and p.get("primary") != account_id
                and p.get("hedge") != account_id
            ]
            if after_pairs != before_pairs:
                new_config["pairs"] = after_pairs
                did_change = True

        if did_change:
            await db.execute(
                text(
                    "UPDATE strategies SET config = CAST(:config AS jsonb), updated_at = NOW() WHERE id = CAST(:id AS uuid)"
                ),
                {"id": sid, "config": json.dumps(new_config)},
            )
            changed += 1

    if changed:
        await db.commit()

    # 3) Alert
    await db.execute(
        text(
            "INSERT INTO alerts (type, title, message, data) VALUES (:type, :title, :message, CAST(:data AS jsonb))"
        ),
        {
            "type": "account",
            "title": "Account disabled",
            "message": f"Account {result.get('name')} disabled on {platform}. Removed from {changed} strategies.",
            "data": json.dumps({"account_id": account_id, "platform": platform, "strategies_updated": changed}),
        },
    )
    await db.commit()

    return AccountSummary(
        id=result["id"],
        name=result["name"],
        platform=platform,
        address=result["address"],
        active=result["active"],
    )


@app.delete("/accounts/{platform}/{account_id}")
async def delete_account(platform: str, account_id: str):
    """Delete account"""
    if platform == "predict":
        await predict_service.delete_account(account_id)
    elif platform == "polymarket":
        await polymarket_service.delete_account(account_id)
    else:
        raise HTTPException(400, f"Unknown platform: {platform}")
    
    return {"status": "deleted"}


# ===== Trading =====

@app.post("/trade", response_model=TradeResponse)
async def execute_trade(data: TradeRequest):
    """Execute trade"""
    # Determine platform from account
    # For now, assume predict
    try:
        result = await predict_service.execute_trade(data.model_dump())
        return TradeResponse(
            trade_id=result.get("trade_id", ""),
            status=result.get("status", "submitted"),
            message=result.get("message", "Trade submitted"),
            order_hash=result.get("order_hash"),
        )
    except Exception as e:
        logger.error(f"Trade failed: {e}")
        raise HTTPException(500, str(e))


@app.get("/positions/{platform}/{account_id}")
async def get_positions(platform: str, account_id: str):
    """Get account positions"""
    if platform == "predict":
        return await predict_service.get_positions(account_id)
    elif platform == "polymarket":
        return await polymarket_service.get_positions(account_id)
    else:
        raise HTTPException(400, f"Unknown platform: {platform}")


# ===== Trades =====

@app.get("/trades")
async def list_trades(
    account_id: str | None = None,
    limit: int = Query(default=50, le=200),
):
    """List recent trades (proxied from account service)"""
    try:
        # For now, only Predict trades
        return await predict_service.list_trades(account_id=account_id, limit=limit)
    except Exception as e:
        logger.error(f"Failed to get trades: {e}")
        return []


# ===== Markets =====

@app.post("/markets/sync")
async def sync_markets(
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Fetch markets from Predict.fun and upsert into ClickHouse.

    NOTE: Intentionally minimal: we only ingest basic metadata. Prices/volume/liquidity
    are set to 0 for now (until we add orderbook/price ingestion).

    Auth: uses Settings.predict_api_key if set, otherwise tries to reuse a per-account
    api_key from predict-account DB.
    """
    api_key = settings.predict_api_key
    if not api_key:
        # fallback to any stored per-account api key
        res = await db.execute(text("""
            SELECT api_key
            FROM predict_accounts
            WHERE api_key IS NOT NULL AND api_key <> ''
            LIMIT 1
        """))
        row = res.fetchone()
        api_key = row[0] if row else ""

    if not api_key:
        raise HTTPException(500, "No Predict API key found (set PREDICT_API_KEY or store api_key on an account)")

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            f"{settings.predict_api_url}/v1/markets",
            params={"limit": limit},
            headers={
                "x-api-key": api_key,
                "User-Agent": "Mozilla/5.0",
            },
        )
        r.raise_for_status()
        payload = r.json()

    markets = payload.get("data") or []
    ch = get_clickhouse()

    column_names = [
        "market_id",
        "platform",
        "question",
        "category",
        "end_date",
        "liquidity",
        "volume",
        "yes_price",
        "no_price",
    ]

    rows: list[list] = []
    def _parse_dt(s: str | None):
        if not s:
            return datetime.utcfromtimestamp(0)
        try:
            # Handle 'Z'
            if s.endswith('Z'):
                s = s[:-1] + '+00:00'
            return datetime.fromisoformat(s)
        except Exception:
            return datetime.utcfromtimestamp(0)

    for m in markets:
        created_at = _parse_dt(m.get("createdAt"))
        rows.append([
            str(m.get("id")),
            "predict",
            m.get("question") or m.get("title") or "",
            m.get("categorySlug") or "",
            created_at,
            0.0,  # liquidity
            0.0,  # volume
            0.0,  # yes_price
            0.0,  # no_price
        ])

    if rows:
        ch.insert("markets.markets", rows, column_names=column_names)

    return {"inserted": len(rows)}


@app.get("/markets", response_model=list[MarketSummary])
async def list_markets(
    platform: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(default=50, le=200),
):
    """List markets from ClickHouse"""
    try:
        ch = get_clickhouse()
        
        query = "SELECT * FROM markets.markets"
        conditions = []
        params = {}
        
        if platform:
            conditions.append("platform = %(platform)s")
            params["platform"] = platform
        
        if category:
            conditions.append("category = %(category)s")
            params["category"] = category
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += f" ORDER BY volume DESC LIMIT {limit}"
        
        result = ch.query(query, parameters=params)
        
        markets = []
        for row in result.result_rows:
            markets.append(MarketSummary(
                market_id=row[0],
                platform=row[1],
                question=row[2],
                category=row[3],
                # schema: market_id, platform, question, category, end_date, liquidity, volume, yes_price, no_price, updated_at
                yes_price=row[7],
                no_price=row[8],
                volume_24h=row[6],
                liquidity=row[5],
            ))
        
        return markets
        
    except Exception as e:
        logger.error(f"Failed to get markets: {e}")
        return []


# ===== Strategies =====

@app.get("/strategies", response_model=list[StrategyDetail])
async def list_strategies(db: AsyncSession = Depends(get_db)):
    """List all strategies"""
    result = await db.execute(text("""
        SELECT id, name, type, config, enabled, created_at
        FROM strategies
        ORDER BY created_at DESC
    """))
    
    strategies = []
    for row in result.fetchall():
        strategies.append(StrategyDetail(
            id=str(row[0]),
            name=row[1],
            type=row[2],
            config=row[3] or {},
            enabled=row[4],
            created_at=row[5],
        ))
    
    return strategies


@app.post("/strategies", response_model=StrategyDetail)
async def create_strategy(data: StrategyCreate, db: AsyncSession = Depends(get_db)):
    """Create new strategy"""
    from sqlalchemy import insert
    from sqlalchemy import Table, Column, String, Boolean, DateTime, MetaData
    from sqlalchemy.dialects.postgresql import UUID, JSONB
    
    # Use raw SQL with proper casting
    config_json = json.dumps(data.config)
    result = await db.execute(text(
        "INSERT INTO strategies (name, type, config, enabled) "
        "VALUES (:name, :type, CAST(:config AS jsonb), :enabled) "
        "RETURNING id, name, type, config, enabled, created_at"
    ).bindparams(
        name=data.name,
        type=data.type,
        config=config_json,
        enabled=data.enabled,
    ))
    await db.commit()
    
    row = result.fetchone()
    return StrategyDetail(
        id=str(row[0]),
        name=row[1],
        type=row[2],
        config=row[3] or {},
        enabled=row[4],
        created_at=row[5],
    )


@app.put("/strategies/{strategy_id}", response_model=StrategyDetail)
async def update_strategy(
    strategy_id: str,
    data: StrategyUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update strategy"""
    updates = []
    params = {"id": strategy_id}
    
    if data.name is not None:
        updates.append("name = :name")
        params["name"] = data.name
    
    if data.config is not None:
        updates.append("config = CAST(:config AS jsonb)")
        params["config"] = json.dumps(data.config)
    
    if data.enabled is not None:
        updates.append("enabled = :enabled")
        params["enabled"] = data.enabled
    
    if not updates:
        raise HTTPException(400, "No fields to update")
    
    query = text(f"""
        UPDATE strategies
        SET {", ".join(updates)}, updated_at = NOW()
        WHERE id = CAST(:id AS uuid)
        RETURNING id, name, type, config, enabled, created_at
    """)
    result = await db.execute(query.bindparams(**params))
    await db.commit()
    
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "Strategy not found")
    
    return StrategyDetail(
        id=str(row[0]),
        name=row[1],
        type=row[2],
        config=row[3] or {},
        enabled=row[4],
        created_at=row[5],
    )


@app.delete("/strategies/{strategy_id}")
async def delete_strategy(strategy_id: str, db: AsyncSession = Depends(get_db)):
    """Delete strategy"""
    result = await db.execute(text("""
        DELETE FROM strategies WHERE id = :id::uuid
    """), {"id": strategy_id})
    await db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(404, "Strategy not found")
    
    return {"status": "deleted"}


# ===== Alerts =====

@app.get("/alerts", response_model=list[AlertResponse])
async def list_alerts(
    unread_only: bool = False,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List alerts"""
    query = "SELECT id, type, title, message, data, read, created_at FROM alerts"
    
    if unread_only:
        query += " WHERE read = false"
    
    query += f" ORDER BY created_at DESC LIMIT {limit}"
    
    result = await db.execute(text(query))
    
    alerts = []
    for row in result.fetchall():
        alerts.append(AlertResponse(
            id=str(row[0]),
            type=row[1],
            title=row[2],
            message=row[3],
            data=row[4],
            read=row[5],
            created_at=row[6],
        ))
    
    return alerts


@app.post("/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: str, db: AsyncSession = Depends(get_db)):
    """Mark alert as read"""
    await db.execute(text("""
        UPDATE alerts SET read = true WHERE id = :id::uuid
    """), {"id": alert_id})
    await db.commit()
    return {"status": "ok"}


@app.post("/alerts/read-all")
async def mark_all_alerts_read(db: AsyncSession = Depends(get_db)):
    """Mark all alerts as read"""
    await db.execute(text("UPDATE alerts SET read = true WHERE read = false"))
    await db.commit()
    return {"status": "ok"}


# ===== WebSocket =====

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    ws_connections.add(websocket)
    
    try:
        while True:
            # Keep connection alive, handle incoming messages
            data = await websocket.receive_text()
            # Could handle subscriptions here
            
    except WebSocketDisconnect:
        pass
    finally:
        ws_connections.discard(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
