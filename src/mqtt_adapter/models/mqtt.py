from typing import Dict, List, Optional
from .base import BaseModel

class MQTTRequest(BaseModel):
    """MQTT request model"""
    topic: str
    payload: dict
    correlation_id: str
    target_broker_id: str
    is_response: bool = False

    def to_dict(self) -> dict:
        """Convert the model to a dictionary"""
        return self.dict()

class MQTTResponse(BaseModel):
    """MQTT response model"""
    status_code: int
    payload: dict
    correlation_id: str

    def to_dict(self) -> dict:
        """Convert the model to a dictionary"""
        return self.dict()

class MQTTBrokerConfig(BaseModel):
    """MQTT broker configuration"""
    broker_id: str
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: str
    clean_session: bool = True
    qos: int = 0
    keepalive: int = 60
    subscribe_topics: List[str] = []
    
    

class MQTTAppConfig(BaseModel):
    """Application configuration containing all broker configurations"""
    brokers: Dict[str, MQTTBrokerConfig]

    @classmethod
    def load_from_file(cls, file_path: str) -> 'MQTTAppConfig':
        """Load the configuration from a file"""
        import json
        import yaml
        
        if file_path.endswith('.json'):
            with open(file_path, 'r') as f:
                data = json.load(f)
        elif file_path.endswith(('.yaml', '.yml')):
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")
        
        # Convert dict to MQTTBrokerConfig objects
        for broker_id, broker_data in data.get('brokers', {}).items():
            broker_data['broker_id'] = broker_id  # Ensure broker_id is set
            data['brokers'][broker_id] = MQTTBrokerConfig(**broker_data)
            
        return cls(**data)
    
    def get_broker_config(self, broker_id: str) -> MQTTBrokerConfig:
        """Get a broker configuration by ID"""
        if broker_id not in self.brokers:
            raise KeyError(f"Broker ID not found: {broker_id}")
        return self.brokers[broker_id]
    
    def get_all_broker_ids(self) -> List[str]:
        """Get all broker IDs"""
        return list(self.brokers.keys()) 