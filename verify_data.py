import psycopg2
import pandas as pd
import time

def check_data():
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="iot_monitoring",
            user="iotuser",
            password="iotpass123" 
        )
        print("✅ Database connection successful!")
        
        # Check raw table
        query = "SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT 5;"
        df = pd.read_sql(query, conn)
        
        if not df.empty:
            print(f"\n🎉 SUCCESS! Found {len(df)} recent records in 'sensor_readings':")
            print(df[['sensor_id', 'location', 'temperature', 'timestamp']])
        else:
            print("\n⚠️ Connection worked, but table 'sensor_readings' is empty.")
            
        conn.close()
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    check_data()