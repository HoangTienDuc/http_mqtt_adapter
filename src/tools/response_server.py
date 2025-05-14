import paho.mqtt.client as mqtt
import json
import time
import logging
import uuid
from copy import deepcopy

# Cấu hình logging để dễ theo dõi
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MQTTListener:
    """
    MQTT Listener để lắng nghe topic requests và trả lời về topic tmp
    """
    
    def __init__(
        self, 
        broker_host="localhost", 
        broker_port=1883, 
        client_id=None,
        subscibe_topic="requests",
    ):
        # Thông tin kết nối broker
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = client_id or f"mqtt-listener-{uuid.uuid4().hex[:8]}"
        
        self.subscibe_topic = subscibe_topic
        # Tạo MQTT client
        self.client = mqtt.Client(client_id=self.client_id)
        
        # Cài đặt các callback
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        # Biến kiểm soát
        self.running = True
    
    def _on_connect(self, client, userdata, flags, rc):
        """Xử lý sự kiện kết nối thành công"""
        if rc == 0:
            logger.info(f"Đã kết nối tới MQTT broker tại {self.broker_host}:{self.broker_port}")
            # Subscribe vào topic requests
            client.subscribe(self.subscibe_topic, qos=1)
            logger.info(f"Đã subscribe vào topic: {self.subscibe_topic}")
        else:
            logger.error(f"Không thể kết nối tới broker, mã lỗi: {rc}")
            
    def _on_disconnect(self, client, userdata, rc):
        """Xử lý sự kiện ngắt kết nối"""
        if rc != 0:
            logger.warning(f"Ngắt kết nối không mong muốn, mã lỗi: {rc}")
        else:
            logger.info("Đã ngắt kết nối từ broker")
    
    def _on_message(self, client, userdata, message):
        """Xử lý khi nhận được tin nhắn từ topic requests"""
        try:
            logger.info(f"Nhận được tin nhắn trên topic: {message.topic}")
            
            # Giải mã payload từ bytes sang string
            payload_str = message.payload.decode('utf-8')
            
            # Parse JSON nếu có thể, nếu không thì giữ nguyên string
            try:
                payload = json.loads(payload_str)
                logger.info(f"Nội dung tin nhắn (JSON): {payload}")
            except json.JSONDecodeError:
                payload = payload_str
                logger.info(f"Nội dung tin nhắn (raw): {payload}")
            
            identifier = payload.get('identifier', '')
            response_payload = deepcopy(payload)
            response_payload["identifier"] = self.client_id
            response_payload["payload"]["message"] = f"Response from {self.client_id}"
            # Gửi response về topic tmp
            result = client.publish(identifier, json.dumps(response_payload), qos=1)
            
            # Kiểm tra kết quả publish
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Đã gửi phản hồi tới topic: {identifier}")
            else:
                logger.error(f"Lỗi khi gửi phản hồi: {mqtt.error_string(result.rc)}")
                
        except Exception as e:
            logger.error(f"Lỗi xử lý tin nhắn: {str(e)}")
    
    def start(self):
        """Bắt đầu lắng nghe"""
        try:
            # Kết nối tới broker
            logger.info(f"Đang kết nối tới {self.broker_host}:{self.broker_port}...")
            self.client.connect(self.broker_host, self.broker_port, 60)
            
            # Bắt đầu vòng lặp lắng nghe
            logger.info("Bắt đầu lắng nghe tin nhắn...")
            self.client.loop_forever()
        except KeyboardInterrupt:
            logger.info("Đã nhận tín hiệu dừng từ người dùng")
        except Exception as e:
            logger.error(f"Lỗi: {str(e)}")
        finally:
            self.stop()
    
    def stop(self):
        """Dừng lắng nghe và dọn dẹp tài nguyên"""
        self.running = False
        if self.client:
            self.client.disconnect()
            logger.info("Đã ngắt kết nối MQTT")

if __name__ == "__main__":
    # Khởi tạo listener
    listener = MQTTListener(
        broker_host="192.168.1.19",  # Thay đổi tùy theo broker của bạn
        broker_port=1883,         # Thay đổi tùy theo cấu hình broker
        subscibe_topic="requests/#", # Topic lắng nghe
        client_id="response_server"
    )
    
    try:
        # Bắt đầu lắng nghe
        listener.start()
    except KeyboardInterrupt:
        print("\nNgắt bởi người dùng. Thoát chương trình.")
