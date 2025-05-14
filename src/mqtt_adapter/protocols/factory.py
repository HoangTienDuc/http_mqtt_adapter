import asyncio
from typing import Dict

from ..models import MQTTAppConfig
from .base import BaseProtocol, MQTTBrokerRegistry

class MQTTProtocolFactory:
    """Factory for creating MQTT protocol instances from configuration"""
    
    @staticmethod
    def create_protocols(
        config: MQTTAppConfig, 
        registry: MQTTBrokerRegistry, 
        loop: asyncio.AbstractEventLoop
    ) -> Dict[str, BaseProtocol]:
        """Create protocol instances for all brokers in the configuration"""
        protocols = {}
        
        for broker_id, broker_config in config.brokers.items():
            protocol = BaseProtocol(
                config=broker_config,
                broker_registry=registry,
                loop=loop
            )
            protocols[broker_id] = protocol
            registry.register_protocol(broker_id, protocol)
        
        return protocols 