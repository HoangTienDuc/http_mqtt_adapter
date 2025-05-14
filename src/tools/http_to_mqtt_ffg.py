import requests
import json
import uuid
import time
import logging
from typing import Dict, Any, Optional

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HTTPtoMQTTClient:
    """
    Client để gửi request HTTP đến adapter và chuyển tiếp đến MQTT
    """
    
    def __init__(self, adapter_url: str = "http://localhost:8080"):
        """
        Khởi tạo client với URL của adapter
        
        Args:
            adapter_url: URL cơ sở của adapter (mặc định: http://localhost:8080)
        """
        self.adapter_url = adapter_url.rstrip('/')
        self.session = requests.Session()
        # Thêm headers mặc định nếu cần
        self.session.headers.update({
            "Content-Type": "application/json"
        })
    
    def check_health(self) -> Dict[str, Any]:
        """
        Kiểm tra trạng thái của adapter
        
        Returns:
            Dict chứa thông tin trạng thái
        """
        try:
            response = self.session.get(f"{self.adapter_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra trạng thái: {e}")
            return {"error": str(e), "status": "error"}
    
    def send_request(
        self,
        correlation_id: str,
        identifier: str,
        request_topic: str,
        is_request: bool,
        payload: Dict[str, Any],
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Gửi request HTTP đến adapter để chuyển tiếp đến MQTT broker
        
        Args:
            broker_id: ID của broker MQTT đích (vd: "internet 1", "local")
            topic: Topic MQTT cần publish
            payload: Dữ liệu cần gửi
            correlation_id: ID tương quan (tạo mới nếu không cung cấp)
            timeout: Thời gian chờ tối đa (giây)
            
        Returns:
            Dict chứa phản hồi từ MQTT hoặc thông báo lỗi
        """
        # Tạo correlation ID nếu không được cung cấp
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Xây dựng URL endpoint
        endpoint = f"{self.adapter_url}/api/{identifier}/{request_topic}"
        
        # Chuẩn bị payload
        request_data = {
            "is_request": is_request,
            "payload": payload,
        }
        
        # Chuẩn bị headers
        headers = {
            "X-Correlation-ID": correlation_id
        }
        
        try:
            logger.info(f"Gửi request đến: {endpoint}")
            logger.info(f"Correlation ID: {correlation_id}")
            logger.info(f"Payload: {json.dumps(request_data, indent=2)}")
            
            # Gửi request
            start_time = time.time()
            response = self.session.post(
                endpoint, 
                json=request_data, 
                headers=headers,
                timeout=timeout
            )
            
            # Tính thời gian phản hồi
            response_time = time.time() - start_time
            
            # Kiểm tra mã trạng thái
            response.raise_for_status()
            
            # Phân tích phản hồi
            response_data = response.json()
            
            logger.info(f"Nhận được phản hồi sau {response_time:.2f}s")
            logger.info(f"Mã trạng thái: {response.status_code}")
            logger.info(f"Phản hồi: {json.dumps(response_data, indent=2)}")
            
            return response_data
            
        except requests.exceptions.HTTPError as e:
            # logger.error(f"Lỗi HTTP: {e}")
            # Thử phân tích phản hồi lỗi nếu có
            try:
                error_response = e.response.json()
                return {"error": error_response, "status": "error"}
            except:
                return {"error": str(e), "status": "error"}
                
        except requests.exceptions.ConnectionError:
            logger.error(f"Lỗi kết nối đến adapter: {self.adapter_url}")
            return {"error": "Không thể kết nối đến adapter", "status": "error"}
            
        except requests.exceptions.Timeout:
            logger.error(f"Request bị timeout sau {timeout}s")
            return {"error": "Request bị timeout", "status": "error"}
            
        except Exception as e:
            logger.error(f"Lỗi không xác định: {e}")
            return {"error": str(e), "status": "error"}

# Ví dụ sử dụng
def main():
    # Tạo client
    client = HTTPtoMQTTClient("http://localhost:8080")
    
    # Kiểm tra trạng thái adapter
    health = client.check_health()
    if health.get("status") != "ok":
        logger.error(f"Adapter không hoạt động: {health}")
        return
    
    logger.info(f"Adapter hoạt động với các brokers: {health.get('brokers', [])}")
    correlation_id = str(uuid.uuid4())
    broker_id = "internet 2"
    request_topic = f"requests/{broker_id}"
    
    # Ví dụ 1: Gửi thông điệp đến broker internet 1
    response1 = client.send_request(
        correlation_id = correlation_id,
        identifier = broker_id,
        request_topic = request_topic,
        is_request = False,
        payload={
            "message": "Hello from HTTP to MQTT bridge!",
            "timestamp": time.time()
        }
    )
    
    # In kết quả
    logger.info("\n=== Tổng hợp kết quả ===")
    logger.info(f"Kết quả fire and forget pattern: {json.dumps(response1, indent=2)}")

if __name__ == "__main__":
    main()