import time
from mqtt_rrp_pattern import MQTTClient
import uuid

def main():
    # Khởi tạo client
    device_id = "4aa0f6ff-cad4-4fbd-a143-e68971d87230"
    identifier = f"{device_id}"
    
    client = MQTTClient(subcribe_topic=identifier)

    try:
        # Chuẩn bị request data
        payload = {
            "message": f"Hello from identifier",
            "timestamp": str(time.time())
        }
        # Topic to publish to
        request_topic = f"requests/{identifier}"
        
        # Generate correlation ID for tracking the request
        correlation_id = str(uuid.uuid4())
        
        request_data = {
            "payload": payload,
            "correlation_id": correlation_id,
            "identifier": identifier,
            "target_broker_id": "internet 2",
            "is_response": True
        }

        
        # Gửi request và đợi response
        response = client.request(
            topic=request_topic,
            data=request_data,
            timeout=10
        )
        
        if response:
            print("\n[Main] Nhận được response:")
            print(f"[Main] Correlation ID: {response.correlation_id}")
            print(f"[Main] Status: {response.status}")
            # print(f"[Main] Payload: {response.payload}")
        else:
            print("[Main] Không nhận được response trong thời gian chờ")

    except KeyboardInterrupt:
        print("[Main] Dừng chương trình...")
    finally:
        # Cleanup
        client.close()

if __name__ == "__main__":
    main()
