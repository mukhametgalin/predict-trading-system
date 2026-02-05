#!/usr/bin/env python3

"""One-shot roundtrip strategy runner.

- Picks an OPEN market with Yes/No outcomes and a working orderbook
- Buys 1 share YES at a very aggressive price (0.99) to get immediate fill
- Then sells 1 share YES at a very aggressive low price (0.01) to close immediately
- Writes alerts to web-api

Safety:
- Uses tiny size (1 share)
- Uses confirm=true (real orders) ONLY if --confirm passed
"""

from __future__ import annotations

import argparse
import time
from typing import Any

import httpx

WEB_API = "http://localhost:8001"
PREDICT_API = "https://api.predict.fun"

# Repo-local, test API key used elsewhere in the project.
API_KEY = "64f65a47-393c-44f5-bfdc-4d5218dc1ba3"

ACCOUNT_ID = "66ea2188-cb3f-4047-af49-50a3bffe1c7e"  # TestAccount1


def post_alert(c: httpx.Client, title: str, message: str, data: dict[str, Any] | None = None):
    c.post(
        f"{WEB_API}/alerts",
        json={"type": "strategy", "title": title, "message": message, "data": data or {}},
        timeout=10.0,
    ).raise_for_status()


def pick_market() -> str:
    with httpx.Client(timeout=30.0) as c:
        r = c.get(
            f"{PREDICT_API}/v1/markets",
            headers={"x-api-key": API_KEY},
            params={"status": "OPEN", "limit": 50},
        )
        r.raise_for_status()
        markets = r.json().get("data", [])

        for m in markets:
            mid = str(m.get("id"))
            # Ensure details include outcomes
            rr = c.get(f"{PREDICT_API}/v1/markets/{mid}", headers={"x-api-key": API_KEY})
            if rr.status_code != 200:
                continue
            md = rr.json().get("data", rr.json())
            outcomes = md.get("outcomes", [])
            names = {str(o.get("name") or o.get("title") or "").lower() for o in outcomes}
            if not ("yes" in names and "no" in names):
                continue

            ob = c.get(f"{PREDICT_API}/v1/markets/{mid}/orderbook", headers={"x-api-key": API_KEY})
            if ob.status_code != 200:
                continue
            book = ob.json().get("data", ob.json())
            asks = book.get("asks", [])
            bids = book.get("bids", [])
            if not asks or not bids:
                continue

            return mid

    raise RuntimeError("No suitable OPEN market found")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true", help="actually place real orders")
    ap.add_argument("--shares", type=float, default=1.0)
    args = ap.parse_args()

    confirm = bool(args.confirm)

    market_id = pick_market()

    with httpx.Client(timeout=60.0) as c:
        post_alert(
            c,
            "Roundtrip strategy starting",
            f"market_id={market_id} account_id={ACCOUNT_ID} confirm={confirm}",
            {"market_id": market_id, "account_id": ACCOUNT_ID, "confirm": confirm},
        )

        # BUY YES aggressively (should cross the ask)
        buy_req = {
            "account_id": ACCOUNT_ID,
            "market_id": market_id,
            "side": "yes",
            "price": 0.99,
            "shares": float(args.shares),
            "confirm": confirm,
        }
        buy = c.post(f"{WEB_API}/trade", json=buy_req)
        buy.raise_for_status()
        buy_res = buy.json()
        post_alert(
            c,
            "Roundtrip buy submitted",
            str(buy_res.get("message")),
            {"market_id": market_id, "side": "yes", "action": "buy", "resp": buy_res},
        )

        # Small pause so it can fill
        time.sleep(2.0)

        # SELL YES aggressively (should cross the bid)
        sell_req = {
            "account_id": ACCOUNT_ID,
            "market_id": market_id,
            "side": "yes",
            "price": 0.01,
            "shares": float(args.shares),
            "confirm": confirm,
        }
        sell = c.post(f"{WEB_API}/trade", json=sell_req)
        sell.raise_for_status()
        sell_res = sell.json()
        post_alert(
            c,
            "Roundtrip sell submitted",
            str(sell_res.get("message")),
            {"market_id": market_id, "side": "yes", "action": "sell", "resp": sell_res},
        )

        post_alert(
            c,
            "Roundtrip strategy done",
            f"Done for market_id={market_id} confirm={confirm}",
            {"market_id": market_id, "confirm": confirm},
        )

        print("OK", {"market_id": market_id, "confirm": confirm})


if __name__ == "__main__":
    main()
