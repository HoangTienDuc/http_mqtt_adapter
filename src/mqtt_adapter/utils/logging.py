import logging
import sys
import os
from typing import Optional

def setup_logging(log_level: str = None, log_file: str = None):
    """
    Set up logging for the application
    
    Args:
        log_level: The log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to a log file
    """
    # Get log level from environment or parameter
    level_name = log_level or os.environ.get('LOG_LEVEL', 'INFO')
    level = getattr(logging, level_name.upper(), logging.INFO)
    
    # Configure logging
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    # Reduce verbosity of third-party libraries
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('paho').setLevel(logging.WARNING)
    
    logging.info(f"Logging initialized at level {level_name}") 