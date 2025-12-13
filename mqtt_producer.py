"""
MQTT IoT Sensor Simulator
Simulates smart city sensors sending temperature, humidity, and pressure data
"""

import paho.mqtt.client as mqtt
import json
import random
import time
from datetime import datetime

# Configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "iot/sensors"

# Sensor locations in a smart city
LOCATIONS = [
    "Downtown", 
    "Industrial_Zone", 
    "Residential_Area", 
    "City_Park", 
    "Highway_A1",
    "Shopping_Mall",
    "University_Campus",
    "Airport",
    "Harbor",
    "Suburb_North"
]

def generate_sensor_data():
    """Generate realistic IoT sensor data"""
    sensor_id = f"SENSOR_{random.randint(1, 10):03d}"
    location = random.choice(LOCATIONS)
    
    # Generate realistic values with some variation
    base_temp = 22.0
    if location == "Industrial_Zone":
        base_temp = 28.0  # Warmer in industrial areas
    elif location == "City_Park":
        base_temp = 20.0  # Cooler in parks
    
    data = {
        "sensor_id": sensor_id,
        "location": location,
        "timestamp": datetime.now().isoformat(),
        "temperature": round(random.uniform(base_temp - 3, base_temp + 3), 2),
        "humidity": round(random.uniform(30.0, 80.0), 2),
        "pressure": round(random.uniform(980.0, 1020.0), 2)
    }
    return data

def main():
    """Main function to run sensor simulator"""
    print("=" * 60)
    print("IoT Sensor Simulator Starting...")
    print("=" * 60)
    
    # Connect to MQTT broker
    client = mqtt.Client()
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print(f"✅ Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        print(f"📡 Publishing to topic: {MQTT_TOPIC}")
        print("-" * 60)
        
        # Generate and publish sensor data continuously
        counter = 0
        while True:
            sensor_data = generate_sensor_data()
            message = json.dumps(sensor_data)
            
            client.publish(MQTT_TOPIC, message)
            counter += 1
            
            print(f"[{counter}] Published: {sensor_data['sensor_id']} | "
                  f"Temp: {sensor_data['temperature']}°C | "
                  f"Humidity: {sensor_data['humidity']}% | "
                  f"Location: {sensor_data['location']}")
            
            time.sleep(2)  # Send data every 2 seconds
            
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("Sensor simulator stopped by user")
        print("=" * 60)
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        client.disconnect()

if __name__ == "__main__":
    main()
