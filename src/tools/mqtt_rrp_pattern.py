import paho.mqtt.client as mqtt
import json
import uuid
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import threading
from queue import Queue

@dataclass
class MQTTResponse:
    correlation_id: str
    payload: Dict[str, Any]
    status: bool = True


class MQTTClient:
    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883, subcribe_topic: str = "#"):
        self.client = mqtt.Client("client")
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.responses: Dict[str, Queue] = {}
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.default_timeout = 10
        self.connected = threading.Event()
        self.subcribe_topic = subcribe_topic
        
        # Khởi động client
        self._start_client()

    def _start_client(self):
        def run_client():
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_forever()

        self.client_thread = threading.Thread(target=run_client, daemon=True)
        self.client_thread.start()

    def _on_connect(self, client, userdata, flags, rc):
        print(f"[Client] Kết nối với mã trạng thái: {rc}")
        self.client.subscribe(self.subcribe_topic)
        print(f"[Client] Subcribe topic: {self.subcribe_topic}")
        self.connected.set()

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            correlation_id = payload.get("request_id")
            print(f"[Client] Nhận được message: {payload}")
            
            if correlation_id and correlation_id in self.responses:
                response = MQTTResponse(
                    correlation_id=correlation_id,
                    payload=payload.get("data", {}),
                    status=payload.get("status", True)
                )
                self.responses[correlation_id].put(response)
        except Exception as e:
            print(f"[Client] Lỗi khi xử lý message: {e}")
            
    def publish(self, topic: str, data: Dict[str, Any]):
        self.client.publish(topic, json.dumps(data))

    def request(self, topic: str, data: Dict[str, Any], timeout: Optional[int] = None) -> Optional[MQTTResponse]:
        # Đợi kết nối được thiết lập
        if not self.connected.wait(timeout=5):
            print("[Client] Không thể kết nối đến MQTT broker")
            return None

        correlation_id = data.get("correlation_id")
        self.responses[correlation_id] = Queue()

        # message = {
        #     "request_id": correlation_id,
        #     "data": data,
        #     "timestamp": time.time(),
        #     "callback_id": None,
        #     "from_topic": self.subcribe_topic
        # }
        
        self.client.publish(topic, json.dumps(data))
        print(f"[Client] Gửi request đến topic: {topic}")

        try:
            timeout = timeout or self.default_timeout
            response = self.responses[correlation_id].get(timeout=timeout)
            print(f"[Client] Nhận được response từ topic: {topic}")
            return response
        except Exception as e:
            print(f"[Client] Lỗi hoặc timeout khi đợi response: {e}")
            return None
        finally:
            del self.responses[correlation_id]

    def close(self):
        self.client.disconnect()
        self.client_thread.join(timeout=1)
