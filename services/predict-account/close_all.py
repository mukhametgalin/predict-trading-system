"""Close-all positions logic (Predict).

This module is intentionally conservative:
- confirm=false returns a plan (no external side effects)
- confirm=true is NOT implemented yet (requires verified market-order payload)

Next steps:
- Use predict-sdk OrderBuilder to build MARKET orders with slippageBps.
- Submit payload to /v1/orders (EIP-712 order structure)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ClosePlanItem:
    market_id: str
    outcome_id: str
    side: str
    shares: float
    action: str  # e.g. "market_sell" / "market_buy"


def _get(d: dict, *keys: str) -> Any:
    for k in keys:
        if k in d:
            return d[k]
    return None


def build_close_all_plan(positions: list[dict]) -> list[ClosePlanItem]:
    """Build a best-effort close plan from raw positions payload."""
    plan: list[ClosePlanItem] = []

    for p in positions or []:
        if not isinstance(p, dict):
            continue

        market_id = _get(p, "market_id", "marketId", "market")
        outcome_id = _get(p, "outcome_id", "outcomeId", "tokenId", "token_id")
        shares = _get(p, "shares", "size", "quantity")
        side = _get(p, "side", "positionSide")

        if market_id is None or outcome_id is None or shares is None:
            # Skip unknown format
            continue

        try:
            shares_f = float(shares)
        except Exception:
            continue

        # For close, we want to SELL our shares (typical). If API describes BUY/SELL, keep as market_sell.
        action = "market_sell"

        plan.append(
            ClosePlanItem(
                market_id=str(market_id),
                outcome_id=str(outcome_id),
                side=str(side) if side is not None else "", 
                shares=shares_f,
                action=action,
            )
        )

    return plan
