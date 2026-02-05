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
    
    # Use account's API key if available
    if account.api_key:
        client = PredictClient(api_key=account.api_key)
    else:
        client = predict_client
    
    # Get market to find outcome ID (needed for both dry-run and confirm)
    market = await client.get_market(trade_request.market_id)

    # Find outcome ID based on side
    outcome_id = None
    desired_name = "Yes" if trade_request.side.lower() == "yes" else "No"
    for outcome in market.get("outcomes", []):
        if str(outcome.get("name", "")).lower() == desired_name.lower():
            outcome_id = outcome.get("onChainId") or outcome.get("id")
            break

    if not outcome_id:
        raise ValueError(
            f"Could not find outcome for side '{trade_request.side}' in market {trade_request.market_id}"
        )

    # Dry-run check
    if not trade_request.confirm:
        # Orderbook is best-effort; may fail for some markets.
        orderbook_depth_text = ""
        try:
            orderbook = await client.get_orderbook(trade_request.market_id)
            orderbook_depth_text = (
                f" Current orderbook depth: {len(orderbook.get('bids', []))} bids, "
                f"{len(orderbook.get('asks', []))} asks."
            )
        except Exception:
            pass

        return {
            "trade_id": None,
            "account_id": account.id,
            "account_name": account.name,
            "market_id": trade_request.market_id,
            "outcome_id": outcome_id,
            "side": trade_request.side,
            "price": trade_request.price,
            "shares": trade_request.shares,
            "order_hash": None,
            "status": "dry_run",
            "message": (
                f"DRY RUN: Would place {trade_request.side.upper()} order for {trade_request.shares} shares @ {trade_request.price}. "
                f"Market: {market.get('title', 'Unknown')}."
                f"{orderbook_depth_text}"
                " Repeat with confirm=true to execute."
            ),
        }

    # Authenticate
    logger.info(f"Authenticating account {account.name} ({account.address})")
    jwt = await client.authenticate(account.private_key)
    
    # Create order
    logger.info(f"Creating order: {trade_request.side.upper()} {trade_request.shares} @ {trade_request.price}")
    
    result = await client.create_order(
        jwt=jwt,
        market_id=trade_request.market_id,
        outcome_id=outcome_id,
        side=trade_request.side,
        price=trade_request.price,
        shares=trade_request.shares,
        proxy_url=None,  # disable proxy for first money test to avoid timeouts
        private_key=account.private_key,
    )
    
    order_hash = result.get("hash") or result.get("orderHash")
    
    logger.info(f"Order created successfully: {order_hash}")
    
    return {
        "trade_id": order_hash,  # Use order hash as trade ID
        "account_id": account.id,
        "account_name": account.name,
        "market_id": trade_request.market_id,
        "outcome_id": outcome_id,
        "side": trade_request.side,
        "price": trade_request.price,
        "shares": trade_request.shares,
        "order_hash": order_hash,
        "status": "submitted",
        "message": f"Order submitted successfully: {order_hash}",
    }
