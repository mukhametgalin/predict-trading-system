"""Market order helpers using predict-sdk."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from predict_sdk import ChainId, OrderBuilder
from predict_sdk.types import (
    Book,
    BuildOrderInput,
    MarketHelperInput,
    OrderBuilderOptions,
)
from predict_sdk.constants import Side

logger = logging.getLogger(__name__)


@dataclass
class MarketOrderPlan:
    market_id: str
    outcome_id: str
    token_id: str
    side: str  # "BUY" or "SELL"
    shares_wei: int
    price_per_share: float
    maker_amount: int
    taker_amount: int
    slippage_bps: int


def parse_orderbook(raw: dict) -> Book:
    """Convert raw API orderbook to SDK Book."""
    data = raw.get("data", raw)
    return Book(
        market_id=int(data.get("marketId", 0)),
        update_timestamp_ms=int(data.get("updateTimestampMs", 0)),
        asks=[(float(p), float(s)) for p, s in data.get("asks", [])],
        bids=[(float(p), float(s)) for p, s in data.get("bids", [])],
    )


def build_market_sell_plan(
    private_key: str,
    predict_account: str | None,
    token_id: str,
    shares_wei: int,
    book: Book,
    slippage_bps: int = 100,
    fee_rate_bps: int = 0,
) -> MarketOrderPlan:
    """Build a market SELL plan (for closing a long position).

    Returns calculated amounts without submitting anything.
    """
    options = OrderBuilderOptions()
    if predict_account:
        options.predict_account = predict_account

    builder = OrderBuilder.make(ChainId.BNB_MAINNET, private_key, options=options)

    # For SELL, we provide quantity (shares we want to sell)
    helper_input = MarketHelperInput(side=Side.SELL, quantity_wei=shares_wei)
    amounts = builder.get_market_order_amounts(helper_input, book)

    return MarketOrderPlan(
        market_id="",  # filled by caller
        outcome_id="",  # filled by caller
        token_id=token_id,
        side="SELL",
        shares_wei=shares_wei,
        price_per_share=amounts.price_per_share,
        maker_amount=amounts.maker_amount,
        taker_amount=amounts.taker_amount,
        slippage_bps=slippage_bps,
    )


def build_market_buy_plan(
    private_key: str,
    predict_account: str | None,
    token_id: str,
    value_wei: int,
    book: Book,
    slippage_bps: int = 100,
    fee_rate_bps: int = 0,
) -> MarketOrderPlan:
    """Build a market BUY plan.

    Returns calculated amounts without submitting anything.
    """
    from predict_sdk.types import MarketHelperValueInput

    options = OrderBuilderOptions()
    if predict_account:
        options.predict_account = predict_account

    builder = OrderBuilder.make(ChainId.BNB_MAINNET, private_key, options=options)

    helper_input = MarketHelperValueInput(side=Side.BUY, value_wei=value_wei)
    amounts = builder.get_market_order_amounts(helper_input, book)

    return MarketOrderPlan(
        market_id="",
        outcome_id="",
        token_id=token_id,
        side="BUY",
        shares_wei=0,
        price_per_share=amounts.price_per_share,
        maker_amount=amounts.maker_amount,
        taker_amount=amounts.taker_amount,
        slippage_bps=slippage_bps,
    )
