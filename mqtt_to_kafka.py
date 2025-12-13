"""
MQTT to Kafka Bridge
Forwards IoT sensor data from MQTT broker to Kafka topic
"""

import paho.mqtt.client as mqtt
from kafka import KafkaProducer
import json
import time

# Configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "iot/sensors"

KAFKA_BROKER = "localhost:9092"
KAFKA_TOPIC = "sensor_data"

# Initialize Kafka producer
producer = None

def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker"""
    if rc == 0:
        print("✅ Connected to MQTT broker")
        client.subscribe(MQTT_TOPIC)
        print(f"📡 Subscribed to topic: {MQTT_TOPIC}")
    else:
        print(f"❌ Connection failed with code {rc}")

def on_message(client, userdata, message):
    """Callback when message received from MQTT"""
    try:
        # Decode message
        payload = json.loads(message.payload.decode())
        
        # Forward to Kafka
        producer.send(KAFKA_TOPIC, payload)
        
        print(f"✅ Forwarded to Kafka: {payload['sensor_id']} | "
              f"Temp: {payload['temperature']}°C")
        
    except Exception as e:
        print(f"❌ Error processing message: {e}")

def main():
    """Main function"""
    global producer
    
    print("=" * 60)
    print("MQTT to Kafka Bridge Starting...")
    print("=" * 60)
    
    # Initialize Kafka producer with retry
    print("Connecting to Kafka...")
    while True:
        try:
            producer = KafkaProducer(
                bootstrap_servers=[KAFKA_BROKER],
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            print(f"✅ Connected to Kafka at {KAFKA_BROKER}")
            break
        except Exception as e:
            print(f"⏳ Waiting for Kafka to be ready... ({e})")
            time.sleep(5)
    
    # Set up MQTT client
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print(f"✅ Connected to MQTT at {MQTT_BROKER}:{MQTT_PORT}")
        print("-" * 60)
        print("Bridge is running. Press Ctrl+C to stop.")
        print("-" * 60)
        
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("Bridge stopped by user")
        print("=" * 60)
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        client.disconnect()
        producer.close()

if __name__ == "__main__":
    main()
