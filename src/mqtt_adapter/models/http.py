from typing import Dict, Optional
from .base import BaseModel

class HTTPRequest(BaseModel):
    """HTTP request model"""
    method: str
    path: str
    headers: Dict[str, str]
    body: Dict[str, any]
    identifier: str
    request_topic: Optional[str] = None

class HTTPResponse(BaseModel):
    """HTTP response model"""
    status_code: int
    headers: Dict[str, str]
    body: Dict[str, any] 