import argparse
import asyncio
import logging
import os
import signal
import sys
from typing import Dict, Any

from .config import load_config
from .models import MQTTAppConfig
from .services import MQTTServiceManager
from .web import WebServer
from .utils import setup_logging

logger = logging.getLogger(__name__)

class MQTTAdapterApp:
    """Main application class for the MQTT Adapter"""
    
    def __init__(self, config_path: str = None):
        self.loop = asyncio.get_event_loop()
        self.config = load_config(config_path)
        self.mqtt_manager = MQTTServiceManager(self.config, self.loop)
        
        # Get web server config from environment
        host = os.environ.get('HTTP_HOST', '0.0.0.0')
        port = int(os.environ.get('HTTP_PORT', '8080'))
        self.web_server = WebServer(self.mqtt_manager, self.loop, host, port)
        
        # Set up signal handlers
        for sig in (signal.SIGINT, signal.SIGTERM):
            self.loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))
    
    async def start(self):
        """Start the application"""
        logger.info("Starting MQTT Adapter")
        
        # Initialize the MQTT service manager
        await self.mqtt_manager.initialize()
        
        # Start the web server
        await self.web_server.start()
        
        logger.info("MQTT Adapter started")
    
    async def shutdown(self):
        """Shutdown the application"""
        logger.info("Shutting down MQTT Adapter")
        
        # Stop the web server
        await self.web_server.stop()
        
        # Shutdown the MQTT service manager
        await self.mqtt_manager.shutdown()
        
        # Stop the event loop
        self.loop.stop()
        
        logger.info("MQTT Adapter shutdown completed")

def main():
    """Main entry point for the application"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='MQTT Adapter')
    parser.add_argument('--config', help='Path to configuration file', default='config.yaml')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Logging level')
    parser.add_argument('--log-file', help='Path to log file', default='mqtt_adapter.log')
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level, args.log_file)
    
    try:
        # Create the application
        app = MQTTAdapterApp(args.config)
        
        # Run the application
        app.loop.create_task(app.start())
        app.loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Application exiting")

if __name__ == '__main__':
    main() 