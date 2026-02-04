"""Predict.fun API client"""

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
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v1/auth/message",
                params={"address": address},
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]
    
    async def get_jwt(self, address: str, signature: str) -> str:
        """Get JWT token with signed message"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/auth/jwt",
                json={
                    "address": address,
                    "signature": signature,
                },
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()
            return data["jwt"]
    
    async def authenticate(self, private_key: str) -> str:
        """Full authentication flow: get message, sign, get JWT"""
        # Get account
        account = Account.from_key(private_key)
        address = account.address
        
        # Get message to sign
        message = await self.get_auth_message(address)
        
        # Sign message
        encoded_message = encode_defunct(text=message)
        signed_message = account.sign_message(encoded_message)
        signature = signed_message.signature.hex()
        
        # Get JWT
        jwt = await self.get_jwt(address, signature)
        
        return jwt
    
    async def get_market(self, market_id: str) -> Dict[str, Any]:
        """Get market details"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v1/markets/{market_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
    
    async def get_orderbook(self, market_id: str) -> Dict[str, Any]:
        """Get market orderbook"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v1/markets/{market_id}/orderbook",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
    
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
        client_kwargs = {}
        if proxy_url:
            client_kwargs["proxies"] = proxy_url
        
        async with httpx.AsyncClient(**client_kwargs) as client:
            response = await client.post(
                f"{self.base_url}/v1/orders",
                json=order_data,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
    
    async def get_positions(self, address: str) -> list[Dict[str, Any]]:
        """Get positions for address"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v1/positions",
                params={"address": address},
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
    
    async def get_orders(self, address: str) -> list[Dict[str, Any]]:
        """Get orders for address"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v1/orders",
                params={"address": address},
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
