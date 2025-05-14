

# MQTT Adapter System

## Configuration

All configurations are stored in `config.yaml`.

> **Note**: Remember to update the **MQTT Internet** settings.
> The **MQTT Internet** broker should be deployed on two separate machines different from your local environment.

---

## System Overview

The system consists of 3 main components:

1. **`main.py`** – The core adapter logic.
2. **Client tools** (located in `src/tools/`):

   * `client_mqtt_to_mqtt_ffg.py`: Fire-and-forget mode – sends messages without expecting a response.
   * `client_mqtt_to_mqtt_rrp.py`: Request-response mode – sends messages and waits for a reply.
3. **Mock Server** – Simulates a server for request-response testing.

---

## How to Run

### Mode: MQTT to MQTT

#### 1. Fire-and-Forget

In this mode, the client sends a message to the source broker. The adapter receives it and forwards it to the destination broker.

**Option 1 – Using Bash Script:**

```bash
bash start_ffg_server.sh
```

**Option 2 – Manual Steps:**

```bash
# 1. Start the adapter
python3 src/main.py

# 2. Send a test message
python3 src/tools/client_mqtt_to_mqtt_ffg.py
```

**Result:**
The adapter will forward the message to the destination broker.
For example, if the client sends a message to broker `0.0.0.0`, the broker at `192.168.1.19` will receive it.

---

#### 2. Request-Response

The client sends a message to the source broker. The adapter forwards it to the destination broker, waits for a response, and then returns the result to the client.

> **Note**: Make sure to stop any previously running `bash` scripts or `main.py` instances before starting this mode.

**Option 1 – Using Bash Script:**

```bash
bash start_rrp_server.sh
python3 src/tools/client_mqtt_to_mqtt_rrp.py
```

**Option 2 – Manual Steps:**

```bash
# 1. Start the adapter
python3 src/main.py

# 2. Start the mock response server
python3 src/tools/response_server.py

# 3. Send a request from the client
python3 src/tools/client_mqtt_to_mqtt_rrp.py

# 4. The client will receive a response
```

---

### Mode: HTTP to MQTT

#### 1. Fire-and-Forget

The client sends an HTTP request to the adapter. The adapter receives the request and forwards it to the destination MQTT broker.

**Option 1 – Using Bash Script:**

```bash
bash start_ffg_server.sh
```

**Option 2 – Manual Steps:**

```bash
# 1. Start the adapter
python3 src/main.py

# 2. Send an HTTP request
python3 src/tools/http_to_mqtt_ffg.py
```

**Result:**
The adapter receives the HTTP request and publishes it to the MQTT broker.
For example, if the client sends the request to `0.0.0.0:8080`, the message will be forwarded to `192.168.1.19`.

---

#### 2. Request-Response

The client sends an HTTP request. The adapter forwards the request to the MQTT broker, waits for a response, and sends the result back as an HTTP response.

> **Note**: Ensure all previous `bash` or `main.py` processes are stopped before proceeding.

**Option 1 – Using Bash Script:**

```bash
bash start_rrp_server.sh
python3 src/tools/http_to_mqtt_rrp.py
```

**Option 2 – Manual Steps:**

```bash
# 1. Start the adapter
python3 src/main.py

# 2. Start the mock response server
python3 src/tools/response_server.py

# 3. Send an HTTP request
python3 src/tools/http_to_mqtt_rrp.py

# 4. The client receives the HTTP response
```

---

Let me know if you'd like to include diagrams, logs, or environment variable setup instructions.
