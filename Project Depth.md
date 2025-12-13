# 🔧 Technical Implementation Documentation
**Project:** Real-Time IoT Monitoring Pipeline
**Course:** ICS-574: Big Data Analytics

This document provides a deep-dive technical analysis of the codebase, explaining the logic, libraries, and data flow mechanisms used to implement the 5-layer architecture.

---

## 1. Infrastructure Layer (Docker & Networking)
**File:** `docker-compose.yml`

The entire backend infrastructure is containerized to ensure reproducibility. We utilize a **Hybrid Deployment Model**:
* **Stateful Services (Docker):** Kafka, Zookeeper, PostgreSQL, and Mosquitto run in isolated containers.
* **Processing Logic (Host):** Python scripts run natively on the host machine to facilitate debugging and visualization.

**Key Configuration Details:**
* **Port Forwarding:** Critical ports (`1883`, `9092`, `5432`) are exposed to `localhost`, allowing the Python scripts running on Windows to communicate seamlessly with the Linux containers.
* **Volume Management:** `postgres_data:/var/lib/postgresql/data` ensures data persistence. Even if containers are destroyed, the historical sensor data remains intact.
* **Service Dependencies:** `depends_on` ensures Kafka does not start until Zookeeper is fully ready.

---

## 2. Ingestion Layer (Edge Simulation)
**File:** `mqtt_producer.py`

This script mimics the behavior of physical IoT devices.

### Technical Logic
1.  **Library Choice:** We use `paho.mqtt.client`, the industry-standard Python client for MQTT, due to its lightweight footprint and robust error handling.
2.  **Data Simulation Algorithm:**
    * Instead of random noise, we implemented **Context-Aware Generation**.
    * *Logic:* `generate_sensor_data()` checks the location. If the location is `Industrial_Zone`, it applies a +6°C offset to the base temperature. If `City_Park`, it applies a -2°C offset.
    * *Noise:* `random.uniform(-3, +3)` is added to mimic sensor jitter.
3.  **Serialization:** Data is packaged into a JSON dictionary containing `sensor_id`, `location`, `timestamp`, `temperature`, `humidity`, and `pressure`.
4.  **Transmission:** Messages are published to the topic `iot/sensors` with QoS 0 (Fire and Forget) to simulate high-throughput sensor telemetry.

---

## 3. The Bridge Layer (Protocol Translation)
**File:** `mqtt_to_kafka.py`

**Problem Solved:** Apache Spark Structured Streaming has excellent native support for Kafka but lacks a built-in MQTT connector. This script bridges that protocol gap.

### Technical Logic
1.  **Asynchronous Callbacks:**
    * We utilize the `on_message(client, userdata, message)` callback from Paho MQTT.
    * This function triggers *interrupt-style* only when a message arrives, preventing CPU waste compared to polling loops.
2.  **Kafka Producer Configuration:**
    * The `KafkaProducer` is initialized with a `value_serializer`.
    * *Code:* `lambda v: json.dumps(v).encode('utf-8')`
    * *Reasoning:* Kafka accepts only bytes. We automatically serialize the incoming JSON object into a UTF-8 byte stream before sending it to the `sensor_data` topic.
3.  **Resiliency (Retry Logic):**
    * The script includes a `while True` loop during initialization. It attempts to connect to Kafka every 5 seconds until successful. This prevents the "Race Condition" where the Python script crashes because the Kafka container hasn't finished booting up.

---

## 4. Processing Layer (Stream Engine)
**File:** `spark_streaming.py`

This is the core engine utilizing **Apache Spark Structured Streaming**.

### A. Environment Configuration
* **Windows Compatibility:** The script auto-detects `JAVA_HOME` and manually injects `hadoop.dll` paths (`winutils.exe`) into the environment variables. This is a critical workaround for running Hadoop/Spark binaries on Windows OS.

### B. Streaming Logic
1.  **Schema Enforcement:**
    * We define a strict `StructType` schema.
    * *Why?* Reading JSON without a schema in streaming allows "schema inference," which is computationally expensive and prone to crashing if a sensor sends bad data. Our approach enforces data types (e.g., `DoubleType` for temperature) immediately.
2.  **Watermarking:**
    * *Code:* `.withWatermark("timestamp", "10 minutes")`
    * *Function:* This handles **Late Data**. Spark maintains the state of the last 10 minutes of aggregation windows. If a data point arrives 2 minutes late due to network lag, Spark updates the previous 5-minute average. If it arrives >10 minutes late, it is dropped to preserve memory stability.
3.  **Windowed Aggregation:**
    * *Code:* `.groupBy(window("timestamp", "5 minutes"), "sensor_id")`
    * This creates a "Tumbling Window," calculating distinct averages for `00:00-00:05`, `00:05-00:10`, etc.

### C. The "Dual-Sink" Pattern
We implement two concurrent write streams using `foreachBatch`:
1.  **Raw Stream:** Appends every record to `sensor_readings`.
2.  **Aggregated Stream:** Appends windowed statistics to `sensor_aggregates`.
* *Optimization:* We use the JDBC driver (`org.postgresql.Driver`) with batch insert support to maximize write throughput to the database.

---

## 5. Storage Layer (Persistence)
**File:** `init.sql`

### Database Design
1.  **Data Types:**
    * `TIMESTAMP` is used (not strings) to allow temporal queries (e.g., "last 1 hour").
    * `DOUBLE PRECISION` is used for metrics to preserve decimal accuracy.
2.  **Performance Optimization (Indexing):**
    * `CREATE INDEX idx_timestamp ON sensor_readings(timestamp DESC);`
    * *Impact:* The dashboard often queries "The last 30 minutes". Without this index, PostgreSQL performs a "Sequential Scan" (reading the whole table). With the B-Tree index, it performs an "Index Scan," jumping directly to the relevant time range. This reduces query latency from O(N) to O(log N).

---

## 6. Visualization & Analytics Layer
**File:** `streamlit_dashboard.py`

### Technical Features
1.  **Caching Strategy:**
    * We use the `@st.cache_data(ttl=5)` decorator on SQL query functions.
    * *Reasoning:* This implements a "Time-to-Live" cache. If multiple users interact with the dashboard simultaneously, the database is queried only once every 5 seconds, preventing connection pool exhaustion.
2.  **Dynamic SQL Generation:**
    * The SQL queries use **Parameterized Queries** (e.g., `WHERE timestamp >= %s`).
    * This prevents SQL Injection vulnerabilities and allows the database engine to cache the execution plan.
3.  **Machine Learning Implementation:**
    * **Library:** `scikit-learn` (`LinearRegression`).
    * **Training Loop:** On every refresh, the dashboard fetches the last 24 hours of data. It transforms the `timestamp` into a numeric Unix epoch format to create the Feature Matrix `X`.
    * **Prediction:** It fits the model $y = mx + c$ to the data and projects $x$ into the future (`current_time + 3600 seconds`) to forecast the temperature.
4.  **Anomaly Detection (IQR):**
    * Instead of fixed thresholds, we calculate the Interquartile Range: $IQR = Q3 - Q1$.
    * Any value falling outside $[Q1 - 1.5*IQR, Q3 + 1.5*IQR]$ is statistically flagged as an anomaly. This allows the system to adapt to different climates (e.g., "Winter" vs "Summer" normals) automatically.