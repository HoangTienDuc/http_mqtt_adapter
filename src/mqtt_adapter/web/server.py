import asyncio
import json
import logging
import uuid
from typing import Optional, Dict, Any
from aiohttp import web

from ..models import HTTPRequest, HTTPResponse, MQTTRequest, MQTTResponse
from ..services import MQTTServiceManager

logger = logging.getLogger(__name__)

class WebServer:
    """
    HTTP Web server that adapts HTTP requests to MQTT requests
    """
    
    def __init__(
        self, 
        mqtt_manager: MQTTServiceManager, 
        loop: Optional[asyncio.AbstractEventLoop] = None,
        host: str = '0.0.0.0',
        port: int = 8080
    ):
        self.mqtt_manager = mqtt_manager
        self.loop = loop or asyncio.get_event_loop()
        self.host = host
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.site = None
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup the routes for the web server"""
        self.app.router.add_post('/api/{identifier}/{request_topic:.*}', self.handle_api_request)
        self.app.router.add_get('/health', self.handle_health_check)
    
    async def start(self):
        """Start the web server"""
        logger.info(f"Starting web server on {self.host}:{self.port}")
        
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        
        logger.info(f"Web server started on http://{self.host}:{self.port}")
    
    async def stop(self):
        """Stop the web server"""
        logger.info("Shutting down web server")
        
        if self.site:
            await self.site.stop()
        
        if self.runner:
            await self.runner.cleanup()
        
        logger.info("Web server shutdown completed")
    
    async def handle_health_check(self, request: web.Request) -> web.Response:
        """Handle health check requests"""
        return web.json_response({
            "status": "ok",
            "service": "mqtt-adapter",
            "brokers": self.mqtt_manager.registry.list_protocols()
        })
    
    async def handle_api_request(self, request: web.Request) -> web.Response:
        """Handle API requests by converting them to MQTT requests"""
        try:
            # Extract broker ID and topic from URL
            identifier = request.match_info['identifier']
            request_topic = request.match_info['request_topic']
            
            # Read request body
            body = await request.json() if request.has_body else {}
            
            # Extract headers
            headers = dict(request.headers)
            
            # Create HTTP request model
            http_request = HTTPRequest(
                method=request.method,
                path=request.path,
                headers=headers,
                body=body,
                identifier=identifier,
                request_topic=request_topic
            )
            
            # Convert to MQTT request
            mqtt_request = await self._convert_to_mqtt_request(http_request)
            
            # Route the request to the MQTT manager
            mqtt_response = await self.mqtt_manager.route_request(mqtt_request)
            
            if mqtt_response is not None:
                # Convert back to HTTP response
                http_response = await self._convert_to_http_response(mqtt_response)
            
                # Remove Content-Type from headers since json_response will set it automatically
                headers = dict(http_response.headers)
                headers.pop('Content-Type', None)
                
                # Convert body to JSON string if it's a dict
                body = json.dumps(http_response.body) if isinstance(http_response.body, (dict, list)) else http_response.body
                
                return web.json_response(
                    body,
                    status=http_response.status_code,
                    headers=headers
                )
            else:
                return web.json_response(
                    {"success": True},
                    status=200
                )
            
        except web.HTTPError as e:
            # Handle HTTP errors
            return web.json_response(
                {"error": str(e)},
                status=e.status
            )
        except Exception as e:
            # Handle other errors
            logger.error(f"Error handling request: {str(e)}", exc_info=True)
            return web.json_response(
                {"error": str(e)},
                status=500
            )
    
    async def _convert_to_mqtt_request(self, http_request: HTTPRequest) -> MQTTRequest:
        """Convert an HTTP request to an MQTT request"""
        # Generate a correlation ID if not provided
        correlation_id = http_request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
        
        # Extract any additional MQTT-specific parameters from the body or headers
        payload: Dict[str, Any] = http_request.body.get('payload', {})
        is_response: bool = http_request.body.get('is_request', False)
        if 'headers' in http_request.body:
            # Remove any headers that were moved to the body to avoid duplication
            for header in http_request.body['headers']:
                if header in payload:
                    logger.warning(f"Header '{header}' appears both in headers and payload, using payload value")
        
        return MQTTRequest(
            topic=http_request.request_topic,
            correlation_id=correlation_id,
            target_broker_id=http_request.identifier,
            is_response=is_response,
            payload=payload
        )
    
    async def _convert_to_http_response(self, mqtt_response: MQTTResponse) -> HTTPResponse:
        """Convert an MQTT response to an HTTP response"""
        # Set appropriate HTTP status code based on MQTT response code
        # Map MQTT status codes to HTTP status codes if needed
        status_code = mqtt_response.status_code
        
        # Set up response headers
        headers = {
            "X-Correlation-ID": mqtt_response.correlation_id,
            "Content-Type": "application/json"
        }
        
        return HTTPResponse(
            status_code=status_code,
            headers=headers,
            body=mqtt_response.payload
        ) 