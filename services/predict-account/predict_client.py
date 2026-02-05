"""Predict.fun API client"""

import asyncio
import httpx
import logging
from typing import Optional, Dict, Any
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

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
            # API returns {success: true, data: {message: "..."}}
            return data["data"]["message"]
    
    async def get_jwt(self, signer: str, signature: str, message: str) -> str:
        """Get JWT token with signed message"""
        # Predict expects signature as 0x-prefixed hex string
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
            # API usually returns {success: true, data: {token: "..."}}
            if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
                return data["data"].get("token") or data["data"].get("jwt")
            return data.get("token") or data.get("jwt")
    
    async def authenticate(self, private_key: str) -> str:
        """Full authentication flow: get message, sign, get JWT"""
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
        """Get market orderbook.

        Predict docs mention `GET /orderbook/{marketId}` but some deployments use
        `GET /v1/markets/{marketId}/orderbook`.

        We try multiple known variants.
        """
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
    ) -> Dict[str, Any]:
        """Create order on Predict.fun"""
        # Build order
        order_data = {
            "marketId": market_id,
            "outcomeId": outcome_id,
            "side": side.upper(),  # YES or NO
            "price": str(price),
            "size": str(shares),
        }
        
        headers = {
            **self.headers,
            "Authorization": f"Bearer {jwt}",
        }
        
        # Create HTTP client with proxy if provided
        client_kwargs = {"timeout": 60.0}
        if proxy_url:
            # httpx>=0.28 uses `proxy=` instead of `proxies=`
            client_kwargs["proxy"] = proxy_url

        last_err = None
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(**client_kwargs) as client:
                    response = await client.post(
                        f"{self.base_url}/v1/orders",
                        json=order_data,
                        headers=headers,
                    )
                    response.raise_for_status()
                    return response.json()
            except (httpx.TransportError, httpx.HTTPStatusError) as e:
                last_err = e
                await asyncio.sleep(1.0 * (attempt + 1))

        raise last_err
    
    async def get_positions(self, address: str, jwt: Optional[str] = None) -> list[Dict[str, Any]]:
        """Get positions for address.

        Predict API requires Authorization header.
        """
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
