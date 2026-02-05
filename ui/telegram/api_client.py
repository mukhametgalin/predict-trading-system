"""Web API Client"""

import httpx
from typing import Optional, Any
from config import settings


class APIClient:
    """Client for Web API Gateway"""
    
    def __init__(self):
        self.base_url = settings.web_api_url
    
    async def _request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> dict | list:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                f"{self.base_url}{path}",
                **kwargs
            )
            response.raise_for_status()
            return response.json()
    
    async def get(self, path: str, **kwargs):
        return await self._request("GET", path, **kwargs)
    
    async def post(self, path: str, **kwargs):
        return await self._request("POST", path, **kwargs)
    
    async def put(self, path: str, **kwargs):
        return await self._request("PUT", path, **kwargs)
    
    async def delete(self, path: str, **kwargs):
        return await self._request("DELETE", path, **kwargs)
    
    # Dashboard
    async def get_stats(self) -> dict:
        return await self.get("/dashboard/stats")
    
    # Accounts
    async def list_accounts(self, platform: str = None) -> list:
        params = {}
        if platform:
            params["platform"] = platform
        return await self.get("/accounts", params=params)
    
    async def get_account(self, platform: str, account_id: str) -> dict:
        return await self.get(f"/accounts/{platform}/{account_id}")
    
    async def toggle_account(self, platform: str, account_id: str, active: bool) -> dict:
        return await self.put(f"/accounts/{platform}/{account_id}", json={"active": active})
    
    # Trading
    async def execute_trade(
        self,
        account_id: str,
        market_id: str,
        side: str,
        price: float,
        shares: float,
        confirm: bool = False,
    ) -> dict:
        return await self.post("/trade", json={
            "account_id": account_id,
            "market_id": market_id,
            "side": side,
            "price": price,
            "shares": shares,
            "confirm": confirm,
        })
    
    # Positions
    async def get_positions(self, platform: str, account_id: str) -> list:
        return await self.get(f"/positions/{platform}/{account_id}")
    
    # Markets
    async def list_markets(self, platform: str = None, limit: int = 20) -> list:
        params = {"limit": limit}
        if platform:
            params["platform"] = platform
        return await self.get("/markets", params=params)
    
    # Strategies
    async def list_strategies(self) -> list:
        return await self.get("/strategies")
    
    async def toggle_strategy(self, strategy_id: str, enabled: bool) -> dict:
        return await self.put(f"/strategies/{strategy_id}", json={"enabled": enabled})
    
    # Alerts
    async def list_alerts(self, unread_only: bool = True, limit: int = 10) -> list:
        params = {"unread_only": str(unread_only).lower(), "limit": limit}
        return await self.get("/alerts", params=params)
    
    async def mark_alert_read(self, alert_id: str) -> dict:
        return await self.post(f"/alerts/{alert_id}/read")
    
    async def mark_all_read(self) -> dict:
        return await self.post("/alerts/read-all")


api = APIClient()
