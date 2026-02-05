"""Service clients for internal microservices"""

import httpx
import logging
from typing import Optional, Any
from config import settings

logger = logging.getLogger(__name__)


class ServiceClient:
    """Base HTTP client for internal services"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    async def _request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                f"{self.base_url}{path}",
                **kwargs
            )
            response.raise_for_status()
            return response.json()
    
    async def get(self, path: str, **kwargs) -> dict:
        return await self._request("GET", path, **kwargs)
    
    async def post(self, path: str, **kwargs) -> dict:
        return await self._request("POST", path, **kwargs)
    
    async def put(self, path: str, **kwargs) -> dict:
        return await self._request("PUT", path, **kwargs)
    
    async def delete(self, path: str, **kwargs) -> dict:
        return await self._request("DELETE", path, **kwargs)


class PredictAccountService(ServiceClient):
    """Client for Predict Account Service"""
    
    def __init__(self):
        super().__init__(settings.predict_account_url)
    
    async def list_accounts(self, active_only: bool = False, tag: str = None) -> list:
        params = {}
        if active_only:
            params["active_only"] = "true"
        if tag:
            params["tag"] = tag
        return await self.get("/accounts", params=params)
    
    async def get_account(self, account_id: str) -> dict:
        return await self.get(f"/accounts/{account_id}")
    
    async def create_account(self, data: dict) -> dict:
        return await self.post("/accounts", json=data)
    
    async def update_account(self, account_id: str, data: dict) -> dict:
        return await self.put(f"/accounts/{account_id}", json=data)
    
    async def delete_account(self, account_id: str) -> dict:
        return await self.delete(f"/accounts/{account_id}")
    
    async def execute_trade(self, data: dict) -> dict:
        return await self.post("/trade", json=data)
    
    async def get_positions(self, account_id: str) -> list:
        return await self.get(f"/positions/{account_id}")

    async def get_orders(self, account_id: str, limit: int = 50) -> list:
        params = {"limit": str(limit)}
        return await self.get(f"/orders/{account_id}", params=params)

    async def list_trades(self, account_id: str | None = None, limit: int = 50) -> list:
        params = {"limit": str(limit)}
        if account_id:
            params["account_id"] = account_id
        return await self.get("/trades", params=params)


class PolymarketAccountService(ServiceClient):
    """Client for Polymarket Account Service"""
    
    def __init__(self):
        super().__init__(settings.polymarket_account_url)
    
    async def list_accounts(self, active_only: bool = False, tag: str = None) -> list:
        params = {}
        if active_only:
            params["active_only"] = "true"
        if tag:
            params["tag"] = tag
        try:
            return await self.get("/accounts", params=params)
        except Exception as e:
            logger.warning(f"Polymarket service not available: {e}")
            return []
    
    async def get_account(self, account_id: str) -> dict:
        return await self.get(f"/accounts/{account_id}")
    
    async def create_account(self, data: dict) -> dict:
        return await self.post("/accounts", json=data)
    
    async def update_account(self, account_id: str, data: dict) -> dict:
        return await self.put(f"/accounts/{account_id}", json=data)
    
    async def delete_account(self, account_id: str) -> dict:
        return await self.delete(f"/accounts/{account_id}")
    
    async def execute_trade(self, data: dict) -> dict:
        return await self.post("/trade", json=data)
    
    async def get_positions(self, account_id: str) -> list:
        return await self.get(f"/positions/{account_id}")


class StrategyEngineService(ServiceClient):
    """Client for Strategy Engine"""
    
    def __init__(self):
        super().__init__(settings.strategy_engine_url)
    
    async def health(self) -> dict:
        try:
            return await self.get("/health")
        except Exception:
            return {"status": "unavailable"}
    
    async def get_stats(self) -> dict:
        try:
            return await self.get("/stats")
        except Exception as e:
            logger.warning(f"Strategy engine not available: {e}")
            return {}


# Singleton instances
predict_service = PredictAccountService()
polymarket_service = PolymarketAccountService()
strategy_service = StrategyEngineService()
