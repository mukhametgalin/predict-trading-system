"""Test: place a LIMIT order using Predict Account (smart wallet) flow.

Usage:
  source .venv/bin/activate
  python scripts/test_place_order_predict_account.py \
    --api-key ... \
    --privy-key ... \
    --predict-account ... \
    --market-id 6714 \
    --outcome Yes \
    --price 0.51 \
    --shares 2

Notes:
- Predict API requires x-api-key for all endpoints.
- Personal endpoints require Authorization: Bearer <token>.
- For Predict Accounts, JWT signature is produced via SDK: builder.sign_predict_account_message(message)
- Order payload is generated via predict-sdk; we then submit to /v1/orders.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

import httpx
from predict_sdk import OrderBuilder, ChainId
from predict_sdk.types import BuildOrderInput, LimitHelperInput
from predict_sdk import Side


BASE = "https://api.predict.fun"


def wei_from_usd_price(p: float) -> int:
    return int(round(p * 10**18))


def wei_from_shares(s: float) -> int:
    return int(round(s * 10**18))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", required=True)
    ap.add_argument("--privy-key", required=True, help="Privy wallet private key (hex, 0x...)")
    ap.add_argument("--predict-account", required=True, help="Predict account / deposit address")
    ap.add_argument("--market-id", required=True)
    ap.add_argument("--outcome", default="Yes", choices=["Yes", "No"])
    ap.add_argument("--price", type=float, required=True)
    ap.add_argument("--shares", type=float, required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    builder = OrderBuilder.make(
        ChainId.BNB_MAINNET,
        args.privy_key,
        # predict_account mode is activated via options
        options=__import__("predict_sdk.types").types.OrderBuilderOptions(predict_account=args.predict_account),
    )

    headers = {"x-api-key": args.api_key}

    with httpx.Client(timeout=30.0) as c:
        # 1) JWT for predict account
        msg_resp = c.get(f"{BASE}/v1/auth/message", headers=headers)
        msg_resp.raise_for_status()
        message = msg_resp.json()["data"]["message"]
        signature = builder.sign_predict_account_message(message)
        if signature and not signature.startswith("0x"):
            signature = "0x" + signature

        auth_resp = c.post(
            f"{BASE}/v1/auth",
            headers=headers,
            json={"signer": args.predict_account, "message": message, "signature": signature},
        )
        auth_resp.raise_for_status()
        token = auth_resp.json()["data"].get("token") or auth_resp.json()["data"].get("jwt")
        if not token:
            raise RuntimeError(f"No token in auth response: {auth_resp.text[:200]}")

        auth_headers = {**headers, "Authorization": f"Bearer {token}"}

        # 2) Market
        market = c.get(f"{BASE}/v1/markets/{args.market_id}", headers=headers).json()["data"]
        fee_bps = market["feeRateBps"]
        is_neg_risk = market.get("isNegRisk", False)
        is_yield_bearing = market.get("isYieldBearing", False)
        outcome = next(o for o in market["outcomes"] if o["name"] == args.outcome)
        token_id = outcome["onChainId"]

        # 3) Amounts
        price_per_share_wei = wei_from_usd_price(args.price)
        qty_wei = wei_from_shares(args.shares)
        amounts = builder.get_limit_order_amounts(
            LimitHelperInput(side=Side.BUY, price_per_share_wei=price_per_share_wei, quantity_wei=qty_wei)
        )

        # 4) Build order
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        order = builder.build_order(
            "LIMIT",
            BuildOrderInput(
                side=Side.BUY,
                token_id=token_id,
                maker_amount=amounts.maker_amount,
                taker_amount=amounts.taker_amount,
                fee_rate_bps=fee_bps,
                signer=args.predict_account,
                expires_at=expires_at,
            ),
        )

        typed = builder.build_typed_data(order, is_neg_risk=is_neg_risk, is_yield_bearing=is_yield_bearing)
        signed = builder.sign_typed_data_order(typed)

        order_sig = signed.signature
        if order_sig and not order_sig.startswith("0x"):
            order_sig = "0x" + order_sig

        side_val = order.side.value if hasattr(order.side, "value") else int(order.side)
        order_payload = {
            "salt": str(order.salt),
            "maker": order.maker,
            "signer": order.signer,
            "taker": order.taker,
            "tokenId": str(order.token_id),
            "makerAmount": str(order.maker_amount),
            "takerAmount": str(order.taker_amount),
            "expiration": str(order.expiration),
            "nonce": str(order.nonce),
            "feeRateBps": str(order.fee_rate_bps),
            "side": side_val,
            "signatureType": int(order.signature_type),
            "signature": order_sig,
        }

        payload = {
            "data": {
                "pricePerShare": str(price_per_share_wei),
                "strategy": "LIMIT",
                "slippageBps": "0",
                "isFillOrKill": False,
                "order": order_payload,
            }
        }

        est_cost = args.price * args.shares
        print(f"PredictAccount={args.predict_account}")
        print(f"Market={market['title']} ({args.market_id})")
        print(f"Outcome={args.outcome} price={args.price} shares={args.shares} cost~${est_cost:.2f}")
        if args.dry_run:
            print("DRY RUN enabled: not sending /v1/orders")
            return

        # 5) Submit
        resp = c.post(f"{BASE}/v1/orders", headers=auth_headers, json=payload)
        print("POST /v1/orders", resp.status_code)
        print(resp.text[:800])

        # 6) List orders
        orders = c.get(f"{BASE}/v1/orders", headers=auth_headers, params={"limit": 5})
        print("GET /v1/orders", orders.status_code)
        print(orders.text[:800])


if __name__ == "__main__":
    main()
