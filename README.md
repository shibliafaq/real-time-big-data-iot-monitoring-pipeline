# 🌡️ Real-Time IoT Monitoring Pipeline

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Spark](https://img.shields.io/badge/Apache%20Spark-3.5+-orange.svg)](https://spark.apache.org)
[![Kafka](https://img.shields.io/badge/Apache%20Kafka-3.x-black.svg)](https://kafka.apache.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://postgresql.org)

> **ICS-574: Big Data Analytics - Course Project**  
> King Fahd University of Petroleum and Minerals  
> Fall 2025

## 📋 Project Overview

This project implements a **complete end-to-end Big Data pipeline** for real-time IoT sensor monitoring in a Smart City context. The system ingests simulated sensor data from 10 locations, processes it through a streaming pipeline, stores it in a database, and visualizes it through an interactive dashboard with ML-powered predictions.

### 🎯 Key Features

- **Real-time data ingestion** from 10 simulated IoT sensors
- **Message buffering** via Apache Kafka for reliable data streaming
- **Stream processing** using Apache Spark with 5-minute window aggregations
- **Persistent storage** in PostgreSQL (raw readings + aggregates)
- **Interactive dashboard** built with Streamlit
- **ML predictions** using Linear Regression for temperature forecasting
- **Anomaly detection** using IQR statistical method
- **Geospatial visualization** of sensor locations

---

## 🏗️ System Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  IoT Sensors │───▶│ MQTT Broker  │───▶│ Kafka Bridge │───▶│ Apache Kafka │───▶│    Spark     │───▶│  PostgreSQL  │───▶│  Streamlit   │
│  (10 units)  │    │ (Mosquitto)  │    │              │    │              │    │  Streaming   │    │   Database   │    │  Dashboard   │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
     Publish           Port 1883         mqtt_to_kafka         Port 9092         5-min Windows      Raw + Aggregates     Port 8501
```

### Component Details

| Component | Technology | Port | Function |
|-----------|------------|------|----------|
| IoT Sensors | `mqtt_producer.py` | N/A | Generate simulated sensor data (temp, humidity, pressure) |
| MQTT Broker | Mosquitto | 1883 | Lightweight message routing for IoT protocols |
| Kafka Bridge | `mqtt_to_kafka.py` | N/A | Protocol translation (MQTT → Kafka) |
| Message Broker | Apache Kafka | 9092 | Distributed streaming & buffering |
| Stream Processing | PySpark | 4040 | Real-time processing & 5-min aggregations |
| Database | PostgreSQL | 5432 | Persistent storage (raw + aggregates) |
| Dashboard | Streamlit | 8501 | Visualization, analytics & ML predictions |

---

## 📁 Project Structure

```
iot-monitoring-pipeline/
├── docker-compose.yml          # Docker services (Kafka, Zookeeper, PostgreSQL, Mosquitto)
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation
├── mosquitto.conf              # MQTT broker configuration
├── init.sql                    # PostgreSQL schema initialization
│
├── mqtt_producer.py            # IoT sensor data simulator
├── mqtt_to_kafka.py            # MQTT to Kafka bridge
├── spark_streaming.py          # Spark stream processing
├── streamlit_dashboard.py      # Visualization dashboard
│
└── docs/
    ├── architecture.png        # System architecture diagram
    └── screenshots/            # Dashboard screenshots
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Docker & Docker Compose
- Java 8+ (for Spark)

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/iot-monitoring-pipeline.git
cd iot-monitoring-pipeline
```

### 2. Start Docker Services

```bash
docker-compose up -d
```

This starts:
- Zookeeper (port 2181)
- Kafka (port 9092)
- PostgreSQL (port 5432)
- Mosquitto MQTT (port 1883)

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize Database

The database is auto-initialized via `init.sql` when Docker starts. Verify with:

```bash
docker exec -it postgres psql -U iotuser -d iot_monitoring -c "\dt"
```

### 5. Run the Pipeline

Open 4 terminal windows and run in order:

**Terminal 1 - MQTT to Kafka Bridge:**
```bash
python mqtt_to_kafka.py
```

**Terminal 2 - Spark Streaming:**
```bash
python spark_streaming.py
```

**Terminal 3 - IoT Sensor Simulator:**
```bash
python mqtt_producer.py
```

**Terminal 4 - Dashboard:**
```bash
streamlit run streamlit_dashboard.py
```

### 6. Access the Dashboard

Open your browser and navigate to: **http://localhost:8501**

---

## 📊 Dashboard Features

### Real-Time Monitoring
- Live sensor metrics (temperature, humidity, pressure)
- Time-series visualizations
- Threshold-based alerts (High Temp >30°C, Low Temp <15°C, High Humidity >80%)
- Alert severity classification (Critical, Warning, Normal)

### Advanced Analytics
- Statistical analysis (mean, std, quartiles, distribution)
- Correlation matrix (Temperature vs Humidity vs Pressure)
- Trend analysis with 20-point moving average
- ML temperature predictions (Linear Regression)
- Geographic sensor map with status indicators

### Performance Metrics
- System health monitoring
- Data ingestion rate tracking
- Processing latency measurement
- Component health checks

---

## 🗄️ Database Schema

### Table: `sensor_readings` (Raw Data)
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| sensor_id | VARCHAR(50) | Sensor identifier |
| location | VARCHAR(100) | Sensor location |
| timestamp | TIMESTAMP | Reading timestamp |
| temperature | FLOAT | Temperature in °C |
| humidity | FLOAT | Humidity in % |
| pressure | FLOAT | Pressure in hPa |

### Table: `sensor_aggregates` (5-min Windows)
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| sensor_id | VARCHAR(50) | Sensor identifier |
| window_start | TIMESTAMP | Window start time |
| window_end | TIMESTAMP | Window end time |
| avg_temperature | FLOAT | Average temperature |
| avg_humidity | FLOAT | Average humidity |
| avg_pressure | FLOAT | Average pressure |
| min_temperature | FLOAT | Minimum temperature |
| max_temperature | FLOAT | Maximum temperature |
| reading_count | INT | Count of readings |

---

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| KAFKA_BROKER | localhost:9092 | Kafka bootstrap server |
| MQTT_BROKER | localhost | MQTT broker host |
| MQTT_PORT | 1883 | MQTT broker port |
| DB_HOST | localhost | PostgreSQL host |
| DB_PORT | 5432 | PostgreSQL port |
| DB_NAME | iot_monitoring | Database name |
| DB_USER | iotuser | Database username |
| DB_PASS | iotpass123 | Database password |

### Sensor Locations

The system simulates 10 smart city locations:
- Downtown, Airport, Industrial Zone, Residential Area
- City Park, Harbor, University Campus, Shopping Mall
- Highway A1, Suburb North

---

## 🧪 Testing

### Verify Kafka Topics
```bash
docker exec -it kafka kafka-topics.sh --list --bootstrap-server localhost:9092
```

### Check PostgreSQL Data
```bash
docker exec -it postgres psql -U iotuser -d iot_monitoring -c "SELECT COUNT(*) FROM sensor_readings;"
```

### Monitor Spark Jobs
Access Spark UI at: **http://localhost:4040**

---

## 📈 Performance Metrics

| Metric | Value |
|--------|-------|
| Sensor Count | 10 |
| Data Generation Rate | ~30 readings/minute |
| Aggregation Window | 5 minutes |
| Dashboard Refresh | 5 seconds (configurable) |
| Processing Latency | < 10 seconds |

---

## 🎓 Course Information

- **Course:** ICS-574 Big Data Analytics
- **Institution:** King Fahd University of Petroleum and Minerals
- **Semester:** Fall 2025
- **Project Type:** Option 2 - Design and Build New Pipeline

---

## 👥 Team Members

| Name | Student ID | Role |
|------|------------|------|
| [Your Name] | [ID] | [Role] |
| [Team Member 2] | [ID] | [Role] |
| [Team Member 3] | [ID] | [Role] |

---

## 📚 References

- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Apache Spark Structured Streaming](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Eclipse Mosquitto](https://mosquitto.org/)

---

## 📄 License

This project is developed for educational purposes as part of the ICS-574 course at KFUPM.

---

## 🙏 Acknowledgments

- Dr. Waleed Al-Gobi (Course Instructor)
- KFUPM ICS Department
- Open-source community for the amazing tools

---

*Last Updated: December 2025*
