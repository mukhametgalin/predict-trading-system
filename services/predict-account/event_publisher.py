"""Event publisher to Redis Streams"""

import json
import logging
from datetime import datetime
from typing import Dict, Any
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class EventPublisher:
    """Publish events to Redis Streams for strategy engine"""
    
    def __init__(self, redis_host: str = "redis", redis_port: int = 6379):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.client = None
    
    async def _get_client(self):
        """Get or create Redis client"""
        if not self.client:
            self.client = await redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True,
            )
        return self.client
    
    async def publish_event(
        self,
        stream_name: str,
        event_type: str,
        data: Dict[str, Any],
    ):
        """Publish event to Redis Stream"""
        client = await self._get_client()
        
        event = {
            "type": event_type,
            "platform": "predict",
            "timestamp": datetime.utcnow().isoformat(),
            "data": json.dumps(data),
        }
        
        try:
            await client.xadd(stream_name, event)
            logger.info(f"Published event: {stream_name} / {event_type}")
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
    
    async def publish_trade_event(self, event_type: str, data: Dict[str, Any]):
        """Publish trade event"""
        await self.publish_event("trade_events", event_type, data)
    
    async def publish_account_event(self, event_type: str, data: Dict[str, Any]):
        """Publish account event"""
        await self.publish_event("account_events", event_type, data)
    
    async def publish_fill_event(self, data: Dict[str, Any]):
        """Publish fill event (most important for strategies)"""
        await self.publish_event("fill_events", "fill", data)
    
    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
