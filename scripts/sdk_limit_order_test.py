#!/usr/bin/env python3
"""Place a LIMIT order on Predict.fun using predict-sdk.

This script is for *careful testing* with very small size.

It:
- fetches market details
- computes price/share in wei
- builds + signs typed data order via predict-sdk
- obtains JWT via /v1/auth (EOA flow)
- submits order via /v1/orders

NOTE: approvals / onchain tx may still be required depending on account state.
"""

import json
import math
import os
from dataclasses import asdict

import httpx
from eth_account import Account
from eth_account.messages import encode_defunct

from predict_sdk import OrderBuilder, ChainId, Side
from predict_sdk.types import LimitHelperInput, BuildOrderInput

BASE = os.getenv("PREDICT_API_URL", "https://api.predict.fun")


def to_wei(x: float) -> int:
    return int(math.floor(x * 10**18))


def main():
    api_key = os.environ["API_KEY"]
    priv_key = os.environ["PRIVATE_KEY"]  # EOA key used for signing
    market_id = os.getenv("MARKET_ID", "6714")
    price = float(os.getenv("PRICE", "0.51"))
    shares = float(os.getenv("SHARES", "1"))
    outcome_name = os.getenv("OUTCOME", "Yes")  # Yes/No

    acct = Account.from_key(priv_key)
    address = acct.address
    print("signer address:", address)

    with httpx.Client(timeout=30.0) as c:
        # 1) market
        m = c.get(f"{BASE}/v1/markets/{market_id}", headers={"x-api-key": api_key}).json()["data"]
        outcome = next(o for o in m["outcomes"] if o["name"].lower() == outcome_name.lower())
        token_id = outcome["onChainId"]
        fee_rate_bps = m.get("feeRateBps", 200)
        is_neg_risk = bool(m.get("isNegRisk"))
        is_yield_bearing = bool(m.get("isYieldBearing"))
        print("market:", m.get("title"), "feeBps=", fee_rate_bps, "negRisk=", is_neg_risk, "yield=", is_yield_bearing)
        print("outcome:", outcome["name"], "token_id:", str(token_id)[:18] + "...")

        # 2) builder
        builder = OrderBuilder.make(ChainId.BNB_MAINNET, priv_key)

        # 3) amounts
        price_per_share_wei = to_wei(price)
        quantity_wei = to_wei(shares)
        amounts = builder.get_limit_order_amounts(
            LimitHelperInput(side=Side.BUY, price_per_share_wei=price_per_share_wei, quantity_wei=quantity_wei)
        )

        # 4) build order
        order = builder.build_order(
            "LIMIT",
            BuildOrderInput(
                side=Side.BUY,
                token_id=token_id,
                maker_amount=amounts.maker_amount,
                taker_amount=amounts.taker_amount,
                fee_rate_bps=fee_rate_bps,
            ),
        )

        typed = builder.build_typed_data(order, is_neg_risk=is_neg_risk, is_yield_bearing=is_yield_bearing)
        signed = builder.sign_typed_data_order(typed)

        # 5) JWT
        msg = c.get(
            f"{BASE}/v1/auth/message",
            headers={"x-api-key": api_key},
            params={"address": address},
        ).json()["data"]["message"]
        sig = acct.sign_message(encode_defunct(text=msg)).signature.hex()
        if not sig.startswith("0x"):
            sig = "0x" + sig
        tok = c.post(
            f"{BASE}/v1/auth",
            headers={"x-api-key": api_key},
            json={"signer": address, "message": msg, "signature": sig},
        ).json()["data"]["token"]

        headers = {"x-api-key": api_key, "Authorization": f"Bearer {tok}"}

        # 6) submit
        order_dict = {
            "hash": signed.hash or "",
            "salt": str(signed.salt),
            "maker": signed.maker,
            "signer": signed.signer,
            "taker": signed.taker,
            "tokenId": str(signed.token_id),
            "makerAmount": str(signed.maker_amount),
            "takerAmount": str(signed.taker_amount),
            "expiration": str(signed.expiration),
            "nonce": str(signed.nonce),
            "feeRateBps": str(signed.fee_rate_bps),
            "side": "BUY" if int(signed.side.value) == 0 else "SELL",
            "signatureType": str(int(signed.signature_type.value)) if hasattr(signed.signature_type, "value") else str(signed.signature_type),
            "signature": signed.signature,
        }

        payload = {
            "data": {
                "pricePerShare": str(price_per_share_wei),
                "strategy": "LIMIT",
                "slippageBps": "0",
                "isFillOrKill": False,
                "order": order_dict,
            }
        }

        r = c.post(f"{BASE}/v1/orders", headers=headers, json=payload)
        print("/v1/orders status:", r.status_code)
        print(r.text[:1000])


if __name__ == "__main__":
    main()
