"""Trade execution logic"""

import logging
from typing import Dict, Any

from models import Account
from schemas import TradeRequest
from predict_client import PredictClient

logger = logging.getLogger(__name__)


async def execute_trade(
    predict_client: PredictClient,
    account: Account,
    trade_request: TradeRequest,
) -> Dict[str, Any]:
    """Execute trade on Predict.fun"""
    
    # Dry-run check
    if not trade_request.confirm:
        # Get market details for dry-run
        market = await predict_client.get_market(trade_request.market_id)
        orderbook = await predict_client.get_orderbook(trade_request.market_id)
        
        return {
            "trade_id": None,
            "account_id": account.id,
            "account_name": account.name,
            "market_id": trade_request.market_id,
            "side": trade_request.side,
            "price": trade_request.price,
            "shares": trade_request.shares,
            "order_hash": None,
            "status": "dry_run",
            "message": f"DRY RUN: Would place {trade_request.side.upper()} order for {trade_request.shares} shares @ {trade_request.price}. "
                       f"Market: {market.get('title', 'Unknown')}. "
                       f"Current orderbook depth: {len(orderbook.get('bids', []))} bids, {len(orderbook.get('asks', []))} asks. "
                       f"Repeat with confirm=true to execute.",
        }
    
    # Authenticate
    logger.info(f"Authenticating account {account.name} ({account.address})")
    jwt = await predict_client.authenticate(account.private_key)
    
    # Get market to find outcome ID
    market = await predict_client.get_market(trade_request.market_id)
    
    # Find outcome ID based on side
    outcome_id = None
    for outcome in market.get("outcomes", []):
        if outcome.get("side", "").lower() == trade_request.side.lower():
            outcome_id = outcome.get("onChainId") or outcome.get("id")
            break
    
    if not outcome_id:
        raise ValueError(f"Could not find outcome for side '{trade_request.side}' in market {trade_request.market_id}")
    
    # Create order
    logger.info(f"Creating order: {trade_request.side.upper()} {trade_request.shares} @ {trade_request.price}")
    
    result = await predict_client.create_order(
        jwt=jwt,
        market_id=trade_request.market_id,
        outcome_id=outcome_id,
        side=trade_request.side,
        price=trade_request.price,
        shares=trade_request.shares,
        proxy_url=account.proxy_url,
    )
    
    order_hash = result.get("hash") or result.get("orderHash")
    
    logger.info(f"Order created successfully: {order_hash}")
    
    return {
        "trade_id": order_hash,  # Use order hash as trade ID
        "account_id": account.id,
        "account_name": account.name,
        "market_id": trade_request.market_id,
        "side": trade_request.side,
        "price": trade_request.price,
        "shares": trade_request.shares,
        "order_hash": order_hash,
        "status": "submitted",
        "message": f"Order submitted successfully: {order_hash}",
    }
