import asyncio
import json
import uuid
from typing import Dict, Callable, Optional, Any, List
import logging
from paho.mqtt import client as mqtt
from paho.mqtt.client import MQTTMessage

from ..models import MQTTBrokerConfig, MQTTRequest, MQTTResponse
from .interface import IMQTTProtocol

logger = logging.getLogger(__name__)

class MQTTBrokerRegistry:
    """Registry for MQTT protocols/brokers"""
    
    def __init__(self):
        self.protocols: Dict[str, 'BaseProtocol'] = {}
    
    def register_protocol(self, broker_id: str, protocol: 'BaseProtocol'):
        """Register a protocol with the registry"""
        self.protocols[broker_id] = protocol
    
    def get_protocol(self, broker_id: str) -> 'BaseProtocol':
        """Get a protocol by broker ID"""
        if broker_id not in self.protocols:
            raise KeyError(f"Protocol not found for broker ID: {broker_id}")
        return self.protocols[broker_id]
    
    def list_protocols(self) -> List[str]:
        """List all registered protocol IDs"""
        return list(self.protocols.keys())

class BaseProtocol(IMQTTProtocol):
    """Base implementation of the MQTT protocol interface"""
    
    def __init__(
        self, 
        config: MQTTBrokerConfig, 
        broker_registry: MQTTBrokerRegistry, 
        loop: Optional[asyncio.AbstractEventLoop] = None
    ):
        self.loop = loop or asyncio.get_event_loop()
        self.config = config
        self._running = False
        self.client = mqtt.Client(client_id=config.client_id, clean_session=config.clean_session)
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._broker_registry = broker_registry
        
        # Set up callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Set up authentication if provided
        if config.username and config.password:
            self.client.username_pw_set(config.username, config.password)
    
    def get_identifier(self) -> str:
        """Get the identifier for the broker"""
        return self.config.broker_id

    def get_qos(self) -> int:
        """Get the QoS for the broker"""
        return self.config.qos
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when the client connects to the broker"""
        if rc == 0:
            logger.info(f"Connected to broker **{self.config.broker_id}** at **{self.config.host}**:**{self.config.port}**")
            
            # Subscribe to all configured topics
            for topic in self.config.subscribe_topics:
                client.subscribe(topic, qos=self.config.qos)
            client.subscribe(self.config.broker_id, qos=self.config.qos)
            logger.info(f"Subscribed to topic **{topic}**")
        else:
            logger.error(f"Failed to connect to broker **{self.config.broker_id}**, return code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects from the broker"""
        if rc != 0:
            logger.warning(f"Unexpected disconnect from broker **{self.config.broker_id}**, return code: {rc}")
        else:
            logger.info(f"Disconnected from broker **{self.config.broker_id}**")
    
    def _on_message(self, client, userdata, message: MQTTMessage):
        """Callback for when a message is received"""
        try:
            # Parse the payload
            payload = json.loads(message.payload.decode())
            correlation_id = payload.get('correlation_id')
            
            if payload.get('identifier') == self.config.broker_id or correlation_id is None:
                return
            # Check if it's a response to a pending request
            if correlation_id and correlation_id in self._pending_requests:
                # Handle the response for a pending request
                future = self._pending_requests.pop(correlation_id)
                response = MQTTResponse(
                    status_code=payload.get('status_code', 200),
                    payload=payload.get('payload', {}),
                    correlation_id=correlation_id
                )
                if not future.done():
                    self.loop.call_soon_threadsafe(future.set_result, response)
            else:
                # Process as a new incoming request
                # Create a task to handle it asynchronously
                request = MQTTRequest(
                    topic=message.topic,
                    payload=payload.get('payload', {}),
                    correlation_id=payload.get('correlation_id', str(uuid.uuid4())),
                    target_broker_id=payload.get('target_broker_id', ''),
                    is_response=payload.get('is_response', False)
                )
                src_indentifier = payload.get('identifier', '')
                print("#" * 100)
                logger.info(f"1. Received message from broker **{self.config.broker_id}** and ready for forward to the target broker **{payload.get('target_broker_id')}** at topic **{message.topic}**")
                asyncio.run_coroutine_threadsafe(self._handle_message(src_indentifier, request), self.loop)
                
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
    
    async def _handle_message(self, src_indentifier: str, request: MQTTRequest) -> MQTTResponse:
        """Handle an incoming message"""
        try:
            # If a target broker is specified, route the request to it
            
            if request.target_broker_id and request.target_broker_id != self.config.broker_id:
                logger.info(f"2. Routing request from broker **{self.config.broker_id}** to broker **{request.target_broker_id}**")
                response = await self._route_to_target_broker(src_indentifier, request)
                return response
            else:
                return MQTTResponse(
                    status_code=200,
                    payload={"message": "Request handled locally"},
                    correlation_id=request.correlation_id
                )
            
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            return MQTTResponse(
                status_code=500,
                payload={"error": str(e)},
                correlation_id=request.correlation_id
            )
    
    
    
    async def _route_to_target_broker(self, src_indentifier: str, request: MQTTRequest) -> MQTTResponse:
        """Route the request to the target broker"""
        try:
            target_protocol = self._broker_registry.get_protocol(request.target_broker_id)
            response = None
            if request.is_response:
                logger.info(f"3. Sending request to broker **{request.target_broker_id}** at topic **{request.topic}**")
                response = await target_protocol.request(
                    topic=request.topic,
                    payload=request.payload,
                    correlation_id=request.correlation_id,
                    timeout=15.0  # Default timeout
                )
                logger.info(f"4. Received response from broker **{request.target_broker_id}** at response topic **{request.topic}**")
                await self.publish(
                    topic=src_indentifier,
                    payload=response.payload,
                    qos=self.config.qos
                )
                logger.info(f"5. Finnaly, Published response back to broker **{self.config.broker_id}** at response topic **{src_indentifier}**")
            else:
                await target_protocol.publish(
                    topic=request.topic,
                    payload=request.payload,
                    qos=target_protocol.get_qos()
                )
                logger.info(f"3. Finnaly, Published request to broker **{request.target_broker_id}** at topic **{request.topic}**")
            return response
        except Exception as e:
            logger.error(f"Error routing to target broker: {str(e)}")
            return MQTTResponse(
                status_code=500,
                payload={"error": f"Failed to route to broker: {request.target_broker_id}: {str(e)}"},
                correlation_id=request.correlation_id
            )
    
    
    async def start(self):
        """Start the MQTT client"""
        if self._running:
            return
        
        # Connect to the broker
        self.client.connect_async(
            host=self.config.host,
            port=self.config.port,
            keepalive=self.config.keepalive
        )
        
        # Start the MQTT loop in a separate thread
        self.client.loop_start()
        self._running = True
        logger.info(f"Started MQTT protocol for broker **{self.config.broker_id}**")
    
    async def stop(self):
        """Stop the MQTT client"""
        if not self._running:
            return
        
        # Cancel any pending requests
        for correlation_id, future in self._pending_requests.items():
            if not future.done():
                future.cancel()
        
        # Disconnect and stop the loop
        self.client.disconnect()
        self.client.loop_stop()
        self._running = False
        logger.info(f"Stopped MQTT protocol for broker **{self.config.broker_id}**")
    
    async def publish(self, topic: str, payload: Dict[str, Any], qos: int = None):
        """Publish a message to a topic"""
        if not self._running:
            raise RuntimeError("MQTT protocol not running")
        
        # Use the configured QoS if not specified
        if qos is None:
            qos = self.config.qos
        
        # Convert the payload to JSON
        message = json.dumps(payload).encode('utf-8')
        
        # Publish the message
        self.client.publish(topic, message, qos=qos)
    
    async def request(
        self, 
        topic: str, 
        payload: Dict[str, Any], 
        correlation_id: str, 
        timeout: float = 30.0
    ) -> MQTTResponse:
        """Send a request and wait for a response"""
        if not self._running:
            raise RuntimeError("MQTT protocol not running")
        
        # Create a future to wait for the response
        future = self.loop.create_future()
        self._pending_requests[correlation_id] = future
        
        # Prepare the payload with correlation ID
        full_payload = {
            "identifier": self.config.broker_id,
            "payload": payload,
            "correlation_id": correlation_id
        }
        
        # Publish the request
        await self.publish(topic, full_payload, self.config.qos)
        
        try:
            # Wait for the response with timeout
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            # Remove the pending request if it times out
            self._pending_requests.pop(correlation_id, None)
            logger.warning(f"Request timed out for correlation ID: {correlation_id}")
            return MQTTResponse(
                status_code=408,
                payload={"error": "Request timed out"},
                correlation_id=correlation_id
            )
        except Exception as e:
            # Remove the pending request if there's an error
            self._pending_requests.pop(correlation_id, None)
            logger.error(f"Error while waiting for response: {str(e)}")
            return MQTTResponse(
                status_code=500,
                payload={"error": str(e)},
                correlation_id=correlation_id
            ) 