"""
Spark Streaming Job
Processes sensor data from Kafka and writes to PostgreSQL
"""

import os
import sys
import glob
import pyspark

# --- CONFIGURATION SECTION ---
# 1. AUTO-DETECT JAVA PATH
java_candidates = glob.glob(r"C:\Program Files\Java\jdk-17*")
if java_candidates:
    JAVA_HOME = java_candidates[0]
    print(f"âœ… Auto-detected Java at: {JAVA_HOME}")
    os.environ['JAVA_HOME'] = JAVA_HOME
    os.environ['PATH'] = os.path.join(JAVA_HOME, 'bin') + os.pathsep + os.environ.get('PATH', '')
else:
    print("âŒ ERROR: Could not find any 'jdk-17' folder in C:\\Program Files\\Java")
    print("Please install Java 17 or check the path.")
    sys.exit(1)

# 2. HADOOP/WINUTILS SETUP
os.environ['HADOOP_HOME'] = r'C:\hadoop'
os.environ['PATH'] = r'C:\hadoop\bin' + os.pathsep + os.environ.get('PATH', '')

# -----------------------------

from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, avg, min as spark_min, max as spark_max, count
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType

# PostgreSQL configuration - FIXED TO MATCH DOCKER-COMPOSE
POSTGRES_URL = "jdbc:postgresql://localhost:5432/iot_monitoring"
POSTGRES_PROPERTIES = {
    "user": "iotuser",
    "password": "iotpass123",
    "driver": "org.postgresql.Driver"
}

# Define schema for incoming sensor data
SENSOR_SCHEMA = StructType([
    StructField("sensor_id", StringType(), True),
    StructField("location", StringType(), True),
    StructField("timestamp", TimestampType(), True),
    StructField("temperature", DoubleType(), True),
    StructField("humidity", DoubleType(), True),
    StructField("pressure", DoubleType(), True)
])

def write_raw_data(batch_df, batch_id):
    """Write raw sensor readings to PostgreSQL"""
    try:
        batch_df.write \
            .jdbc(url=POSTGRES_URL,
                  table="sensor_readings",
                  mode="append",
                  properties=POSTGRES_PROPERTIES)
        print(f"âœ… Batch {batch_id}: Wrote {batch_df.count()} raw records to PostgreSQL")
    except Exception as e:
        print(f"âŒ Error writing batch {batch_id}: {e}")

def write_aggregated_data(batch_df, batch_id):
    """Write aggregated sensor data to PostgreSQL"""
    try:
        if not batch_df.isEmpty():
            batch_df.write \
                .jdbc(url=POSTGRES_URL,
                      table="sensor_aggregates",
                      mode="append",
                      properties=POSTGRES_PROPERTIES)
            print(f"âœ… Batch {batch_id}: Wrote {batch_df.count()} aggregated records to PostgreSQL")
    except Exception as e:
        print(f"âŒ Error writing aggregated batch {batch_id}: {e}")

def main():
    """Main Spark Streaming function"""
    print("=" * 60)
    print("Starting Spark Streaming Job...")
    print("=" * 60)
    
    # Check Winutils
    winutils_path = os.path.join(os.environ['HADOOP_HOME'], 'bin', 'winutils.exe')
    if os.path.exists(winutils_path):
        print(f"âœ… Winutils found at: {winutils_path}")
    else:
        print(f"âŒ ERROR: Winutils NOT found at: {winutils_path}")
        print("Please check C:\\hadoop\\bin\\winutils.exe exists")
        sys.exit(1)
    
    # Detect Spark Version
    spark_version = pyspark.__version__
    print(f"â„¹ï¸ Detected PySpark Version: {spark_version}")
    
    # Construct the matching package name
    if spark_version.startswith("4."):
        print("âš ï¸ PySpark 4.x detected. Switching to Scala 2.13 connector.")
        kafka_package = "org.apache.spark:spark-sql-kafka-0-10_2.13:3.5.1"
    else:
        kafka_package = f"org.apache.spark:spark-sql-kafka-0-10_2.12:{spark_version}"
    
    postgres_package = "org.postgresql:postgresql:42.5.0"
    print(f"ðŸ“¦ Using packages: {kafka_package}, {postgres_package}")
    
    # Create Spark session
    try:
        spark = SparkSession.builder \
            .appName("IoT_Monitoring_Streaming") \
            .config("spark.jars.packages", f"{kafka_package},{postgres_package}") \
            .config("spark.sql.streaming.checkpointLocation", "./checkpoint") \
            .getOrCreate()
        
        spark.sparkContext.setLogLevel("WARN")
        print("âœ… Spark session created successfully")
        
    except Exception as e:
        print("\nâŒ CRITICAL ERROR: Could not create Spark Session.")
        print(f"Error details: {e}")
        sys.exit(1)
    
    # Read from Kafka
    print("ðŸ“¡ Reading from Kafka topic: sensor_data")
    try:
        kafka_df = spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", "localhost:9092") \
            .option("subscribe", "sensor_data") \
            .option("startingOffsets", "latest") \
            .load()
    except Exception as e:
        print(f"âŒ Error connecting to Kafka: {e}")
        sys.exit(1)
    
    # Parse JSON data
    parsed_df = kafka_df \
        .selectExpr("CAST(value AS STRING) as json_str") \
        .select(from_json(col("json_str"), SENSOR_SCHEMA).alias("data")) \
        .select("data.*")
    
    print("âœ… Kafka stream configured")
    
    # Write raw data to PostgreSQL
    print("ðŸ’¾ Starting raw data stream...")
    query_raw = parsed_df.writeStream \
        .foreachBatch(write_raw_data) \
        .outputMode("append") \
        .start()
    
    # Create aggregated view (5-minute windows)
    print("ðŸ“Š Starting aggregated data stream...")
    aggregated_df = parsed_df \
        .withWatermark("timestamp", "10 minutes") \
        .groupBy(
            col("sensor_id"),
            window(col("timestamp"), "5 minutes")
        ) \
        .agg(
            avg("temperature").alias("avg_temperature"),
            avg("humidity").alias("avg_humidity"),
            avg("pressure").alias("avg_pressure"),
            spark_min("temperature").alias("min_temperature"),
            spark_max("temperature").alias("max_temperature"),
            count("*").alias("reading_count")
        ) \
        .select(
            col("sensor_id"),
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            col("avg_temperature"),
            col("avg_humidity"),
            col("avg_pressure"),
            col("min_temperature"),
            col("max_temperature"),
            col("reading_count")
        )
    
    query_agg = aggregated_df.writeStream \
        .foreachBatch(write_aggregated_data) \
        .outputMode("append") \
        .start()
    
    print("-" * 60)
    print("ðŸš€ Spark Streaming is running!")
    print("Press Ctrl+C to stop")
    print("-" * 60)
    
    # Wait for termination
    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    main()