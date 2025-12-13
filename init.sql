-- Create main sensor readings table
CREATE TABLE IF NOT EXISTS sensor_readings (
    id SERIAL PRIMARY KEY,
    sensor_id VARCHAR(50) NOT NULL,
    location VARCHAR(100),  -- <--- THIS WAS MISSING
    timestamp TIMESTAMP NOT NULL,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    pressure DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create aggregated data table
CREATE TABLE IF NOT EXISTS sensor_aggregates (
    id SERIAL PRIMARY KEY,
    sensor_id VARCHAR(50),
    window_start TIMESTAMP,
    window_end TIMESTAMP,
    avg_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    avg_pressure DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    reading_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX idx_sensor_timestamp ON sensor_readings(sensor_id, timestamp DESC);
CREATE INDEX idx_timestamp ON sensor_readings(timestamp DESC);
CREATE INDEX idx_aggregate_time ON sensor_aggregates(window_start DESC);