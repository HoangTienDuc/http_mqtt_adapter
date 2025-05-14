import asyncio
import uuid
import logging
from typing import Callable, Dict, Optional

from ..models import MQTTAppConfig, MQTTRequest, MQTTResponse
from ..protocols import BaseProtocol, MQTTBrokerRegistry, MQTTProtocolFactory

logger = logging.getLogger(__name__)

class MQTTServiceManager:
    """
    Manager for MQTT services, handles initialization, routing and service registration
    """
    
    def __init__(
        self, 
        config: MQTTAppConfig, 
        loop: Optional[asyncio.AbstractEventLoop] = None
    ):
        self.config = config
        self.loop = loop or asyncio.get_event_loop()
        self.registry = MQTTBrokerRegistry()
        self.protocols: Dict[str, BaseProtocol] = {}
    
    async def initialize(self):
        """Initialize all protocols"""
        logger.info("Initializing MQTT Service Manager")
        
        # Create protocols for all brokers
        self.protocols = MQTTProtocolFactory.create_protocols(
            config=self.config,
            registry=self.registry,
            loop=self.loop
        )
        
        # Start all protocols
        for broker_id, protocol in self.protocols.items():
            await protocol.start()
            logger.info(f"Started protocol for broker: {broker_id}")
        
        logger.info(f"MQTT Service Manager initialized with {len(self.protocols)} brokers")
    
    async def shutdown(self):
        """Shutdown all protocols"""
        logger.info("Shutting down MQTT Service Manager")
        
        for broker_id, protocol in self.protocols.items():
            await protocol.stop()
            logger.info(f"Stopped protocol for broker: {broker_id}")
        
        logger.info("MQTT Service Manager shutdown completed")
    
    async def route_request(self, request: MQTTRequest) -> MQTTResponse:
        """Route a request to the appropriate broker"""
        try:
            # Determine the target broker
            target_broker_id = request.target_broker_id
            
            if not target_broker_id:
                return MQTTResponse(
                    status_code=400,
                    payload={"error": "No target broker specified"},
                    correlation_id=request.correlation_id
                )
            
            # Get the protocol for the target broker
            if target_broker_id not in self.protocols:
                return MQTTResponse(
                    status_code=404,
                    payload={"error": f"Broker not found: {target_broker_id}"},
                    correlation_id=request.correlation_id
                )
            
            protocol = self.protocols[target_broker_id]
            
            # Generate a correlation ID if not provided
            correlation_id = request.correlation_id or str(uuid.uuid4())
            is_response = request.is_response
            if is_response:
                # Send the request and wait for the response
                response = await protocol.request(
                    topic=request.topic,
                    payload=request.payload,
                    correlation_id=correlation_id,
                    timeout=30.0
                )
                
                return response
            return None
            
        except Exception as e:
            logger.error(f"Error routing request: {str(e)}")
            return MQTTResponse(
                status_code=500,
                payload={"error": str(e)},
                correlation_id=request.correlation_id or str(uuid.uuid4())
            )
    
    def get_protocol(self, broker_id: str) -> BaseProtocol:
        """Get a protocol by broker ID"""
        return self.registry.get_protocol(broker_id)
