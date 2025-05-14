import os
import logging
from typing import Dict, Any
import yaml
import json

from ..models import MQTTAppConfig

logger = logging.getLogger(__name__)

def load_config(config_path: str = None) -> MQTTAppConfig:
    """Load the application configuration from a file or environment"""
    if config_path and os.path.exists(config_path):
        logger.info(f"Loading configuration from file: {config_path}")
        return MQTTAppConfig.load_from_file(config_path)
    else:
        logger.info("Loading configuration from environment")
        return load_config_from_env()

def load_config_from_env() -> MQTTAppConfig:
    """Load configuration from environment variables"""
    # Get broker configurations from environment
    # Format: MQTT_BROKER_<broker_id>_<property>=<value>
    brokers = {}
    
    for env_name, env_value in os.environ.items():
        if not env_name.startswith('MQTT_BROKER_'):
            continue
        
        parts = env_name.split('_', 3)
        if len(parts) != 4:
            continue
        
        _, _, broker_id, property_name = parts
        property_name = property_name.lower()
        
        if broker_id not in brokers:
            brokers[broker_id] = {'broker_id': broker_id}
        
        # Handle different property types
        if property_name in ('port', 'qos', 'keepalive'):
            brokers[broker_id][property_name] = int(env_value)
        elif property_name in ('clean_session'):
            brokers[broker_id][property_name] = env_value.lower() in ('true', '1', 'yes')
        elif property_name == 'subscribe_topics':
            brokers[broker_id][property_name] = env_value.split(',')
        else:
            brokers[broker_id][property_name] = env_value
    
    # Check if MQTT_CONFIG_JSON environment variable exists
    json_config = os.environ.get('MQTT_CONFIG_JSON')
    if json_config:
        try:
            config_data = json.loads(json_config)
            if 'brokers' in config_data:
                for broker_id, broker_data in config_data['brokers'].items():
                    if broker_id not in brokers:
                        brokers[broker_id] = broker_data
                        brokers[broker_id]['broker_id'] = broker_id
                    else:
                        # Merge with existing config from environment
                        brokers[broker_id].update(broker_data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse MQTT_CONFIG_JSON: {e}")
    
    return MQTTAppConfig(brokers=brokers) 