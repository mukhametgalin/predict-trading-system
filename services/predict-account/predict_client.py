"""Predict.fun API client"""

import asyncio
import httpx
import logging
from typing import Optional, Dict, Any
from eth_account import Account
from eth_account.messages import encode_defunct

logger = logging.getLogger(__name__)


class PredictClient:
    """Client for Predict.fun API"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.predict.fun"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "x-api-key": api_key,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
    
    async def get_auth_message(self, address: str) -> str:
        """Get authentication message to sign"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/v1/auth/message",
                params={"address": address},
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()
            return data["data"]["message"]
    
    async def get_jwt(self, signer: str, signature: str, message: str) -> str:
        """Get JWT token with signed message"""
        if signature and not signature.startswith("0x"):
            signature = "0x" + signature
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/auth",
                json={
                    "signer": signer,
                    "signature": signature,
                    "message": message,
                },
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
                return data["data"].get("token") or data["data"].get("jwt")
            return data.get("token") or data.get("jwt")
    
    async def authenticate(self, private_key: str, predict_account: str = None) -> str:
        """Full authentication flow: get message, sign, get JWT.
        
        If predict_account is provided, uses Predict Account (smart wallet) flow.
        """
        # Ensure 0x prefix
        if not private_key.startswith("0x"):
            private_key = "0x" + private_key
        
        if predict_account:
            # Predict Account flow - use SDK to sign
            from predict_sdk import OrderBuilder, ChainId
            from predict_sdk.types import OrderBuilderOptions
            
            builder = OrderBuilder.make(
                ChainId.BNB_MAINNET,
                private_key,
                options=OrderBuilderOptions(predict_account=predict_account),
            )
            
            # Get message (no address param needed for predict account)
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/v1/auth/message",
                    headers=self.headers,
                )
                response.raise_for_status()
                message = response.json()["data"]["message"]
            
            # Sign with SDK
            signature = builder.sign_predict_account_message(message)
            if signature and not signature.startswith("0x"):
                signature = "0x" + signature
            
            # Get JWT with predict_account as signer
            jwt = await self.get_jwt(predict_account, signature, message)
        else:
            # EOA flow
            account = Account.from_key(private_key)
            address = account.address

            message = await self.get_auth_message(address)

            encoded_message = encode_defunct(text=message)
            signed_message = account.sign_message(encoded_message)
            signature = signed_message.signature.hex()
            if not signature.startswith("0x"):
                signature = "0x" + signature

            jwt = await self.get_jwt(address, signature, message)
        
        if not jwt:
            raise ValueError("JWT not found in auth response")
        return jwt
    
    async def get_market(self, market_id: str) -> Dict[str, Any]:
        """Get market details"""
        last_err = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        f"{self.base_url}/v1/markets/{market_id}",
                        headers=self.headers,
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data.get("data", data)
            except (httpx.TransportError, httpx.HTTPStatusError) as e:
                last_err = e
                await asyncio.sleep(0.5 * (attempt + 1))
        raise last_err
    
    async def get_orderbook(self, market_id: str) -> Dict[str, Any]:
        """Get market orderbook."""
        paths = [
            f"/v1/markets/{market_id}/orderbook",
            f"/orderbook/{market_id}",
            f"/v1/orderbook/{market_id}",
        ]

        last_err = None
        for attempt in range(3):
            for p in paths:
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.get(
                            f"{self.base_url}{p}",
                            headers=self.headers,
                        )
                        response.raise_for_status()
                        data = response.json()
                        return data.get("data", data)
                except (httpx.TransportError, httpx.HTTPStatusError) as e:
                    last_err = e
            await asyncio.sleep(0.5 * (attempt + 1))

        raise last_err
    
    async def create_order(
        self,
        jwt: str,
        market_id: str,
        outcome_id: str,
        side: str,
        price: float,
        shares: float,
        proxy_url: Optional[str] = None,
        private_key: Optional[str] = None,
        predict_account: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create order on Predict.fun using SDK for EIP-712 signing.
        
        If predict_account is provided, uses Predict Account (smart wallet) flow.
        """
        from predict_sdk import OrderBuilder, ChainId
        from predict_sdk.types import BuildOrderInput, LimitHelperInput, OrderBuilderOptions
        from predict_sdk.constants import Side as SDKSide

        if not private_key:
            raise ValueError("private_key required for order creation")

        # Ensure 0x prefix
        if not private_key.startswith("0x"):
            private_key = "0x" + private_key

        # Get market details for fee and token info
        market = await self.get_market(market_id)
        fee_bps = market.get("feeRateBps", 200)
        is_neg_risk = market.get("isNegRisk", False)
        is_yield_bearing = market.get("isYieldBearing", False)

        # Find token_id for the outcome
        token_id = None
        target_name = "yes" if side.lower() == "yes" else "no"
        for o in market.get("outcomes", []):
            name = str(o.get("name") or o.get("title") or "").lower()
            if name == target_name:
                token_id = o.get("onChainId") or o.get("tokenId") or o.get("id")
                break

        if not token_id:
            raise ValueError(f"Could not find token_id for outcome '{side}'")

        # Create order builder
        if predict_account:
            builder = OrderBuilder.make(
                ChainId.BNB_MAINNET,
                private_key,
                options=OrderBuilderOptions(predict_account=predict_account),
            )
        else:
            builder = OrderBuilder.make(ChainId.BNB_MAINNET, private_key)

        # Calculate amounts (SDK uses 1e18 scale)
        sdk_side = SDKSide.BUY if side.lower() == "yes" else SDKSide.SELL
        helper = LimitHelperInput(
            side=sdk_side,
            price_per_share_wei=int(price * 1e18),
            quantity_wei=int(shares * 1e18),
        )
        amounts = builder.get_limit_order_amounts(helper)

        # Build order
        order_input_kwargs = {
            "side": sdk_side,
            "token_id": str(token_id),
            "maker_amount": amounts.maker_amount,
            "taker_amount": amounts.taker_amount,
            "fee_rate_bps": fee_bps,
        }
        if predict_account:
            order_input_kwargs["signer"] = predict_account
        
        order_input = BuildOrderInput(**order_input_kwargs)
        order = builder.build_order("LIMIT", order_input)

        # Build typed data and sign
        typed_data = builder.build_typed_data(
            order, is_neg_risk=is_neg_risk, is_yield_bearing=is_yield_bearing
        )
        signed_order = builder.sign_typed_data_order(typed_data)

        # Build API payload - wrap in "data" as API expects
        sig = signed_order.signature
        if not sig.startswith("0x"):
            sig = "0x" + sig
        
        # pricePerShare in wei (price * 1e18)
        price_per_share_wei = str(int(price * 1e18))
        
        # side and signatureType as integers (matching working script)
        side_val = order.side.value if hasattr(order.side, "value") else int(order.side)
        sig_type_val = int(order.signature_type.value) if hasattr(order.signature_type, "value") else int(order.signature_type)
        
        payload = {
            "data": {
                "pricePerShare": price_per_share_wei,
                "strategy": "LIMIT",
                "slippageBps": "0",
                "isFillOrKill": False,
                "order": {
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
                    "signatureType": sig_type_val,
                    "signature": sig,
                },
            }
        }

        headers = {
            **self.headers,
            "Authorization": f"Bearer {jwt}",
            "Content-Type": "application/json",
        }

        import json as json_lib
        logger.info(f"Order payload: {json_lib.dumps(payload)}")

        client_kwargs = {"timeout": 60.0}
        if proxy_url:
            client_kwargs["proxy"] = proxy_url

        last_err = None
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(**client_kwargs) as client:
                    response = await client.post(
                        f"{self.base_url}/v1/orders",
                        json=payload,
                        headers=headers,
                    )
                    if response.status_code >= 400:
                        logger.error(f"Order API error: {response.status_code} {response.text}")
                    response.raise_for_status()
                    return response.json()
            except (httpx.TransportError, httpx.HTTPStatusError) as e:
                last_err = e
                await asyncio.sleep(1.0 * (attempt + 1))

        raise last_err
    
    async def get_positions(self, address: str, jwt: Optional[str] = None) -> list[Dict[str, Any]]:
        """Get positions for address."""
        headers = dict(self.headers)
        if jwt:
            headers["Authorization"] = f"Bearer {jwt}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/v1/positions",
                params={"address": address},
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", data)

    async def get_orders(self, address: str, jwt: Optional[str] = None) -> list[Dict[str, Any]]:
        """Get orders for address."""
        headers = dict(self.headers)
        if jwt:
            headers["Authorization"] = f"Bearer {jwt}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/v1/orders",
                params={"address": address},
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", data)

    async def get_open_markets(self, limit: int = 50) -> list[Dict[str, Any]]:
        """Get OPEN (active) markets."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/v1/markets",
                params={"status": "OPEN", "limit": limit},
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", data)
