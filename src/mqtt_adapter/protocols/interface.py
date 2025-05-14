from abc import ABC, abstractmethod
from typing import Dict, Any
import asyncio
from ..models import MQTTResponse

class IMQTTProtocol(ABC):
    """Interface for MQTT protocol implementations"""
    
    @abstractmethod
    async def start(self) -> asyncio.Future:
        """Start the MQTT protocol"""
        pass
    
    @abstractmethod
    async def stop(self) -> asyncio.Future:
        """Stop the MQTT protocol"""
        pass
    
    @abstractmethod
    async def publish(self, topic: str, payload: Dict[str, Any], qos: int) -> asyncio.Future:
        """Publish a message to a topic"""
        pass
    
    @abstractmethod
    async def request(
        self, 
        topic: str, 
        payload: Dict[str, Any], 
        correlation_id: str, 
        timeout: float
    ) -> asyncio.Future:
        """Send a request and wait for a response"""
        pass 