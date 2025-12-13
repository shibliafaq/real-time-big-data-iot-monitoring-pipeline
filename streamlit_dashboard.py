"""
IoT Monitoring Dashboard - FINAL VERSION v2
✅ Fixed: Alert details with scrollable container and full details
✅ Fixed: Graphs sync with time range filter
✅ Fixed: Compact horizontal system architecture diagram that fits properly
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
from datetime import datetime, timedelta, date
import time

# ML imports (optional)
try:
    from sklearn.linear_model import LinearRegression
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

# Graphviz import for system architecture
try:
    import graphviz
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="IoT Monitoring Dashboard",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database connection
DB_PARAMS = {
    "host": "localhost",
    "port": 5432,
    "database": "iot_monitoring",
    "user": "iotuser",
    "password": "iotpass123"
}

# Alert thresholds
TEMP_HIGH_THRESHOLD = 30.0
TEMP_LOW_THRESHOLD = 15.0
HUMIDITY_HIGH_THRESHOLD = 80.0

def get_db_connection():
    """Create database connection"""
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        return conn
    except Exception as e:
        st.error(f"❌ Database Connection Failed: {e}")
        return None

def clean_location_name(location):
    """Convert location names to readable format"""
    return location.replace('_', ' ').title()

@st.cache_data(ttl=5)
def fetch_data_by_date_range(start_date, end_date):
    """Fetch sensor readings by date range"""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()

    try:
        query = """
            SELECT sensor_id, location, timestamp, temperature, humidity, pressure
            FROM sensor_readings
            WHERE timestamp >= %s AND timestamp <= %s
            ORDER BY timestamp DESC
        """
        df = pd.read_sql(query, conn, params=(start_date, end_date))
        df['location_clean'] = df['location'].apply(clean_location_name)
        return df
    except Exception as e:
        st.error(f"❌ Query Error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

@st.cache_data(ttl=5)
def fetch_recent_data(hours=24):
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()

    try:
        # OLD CODE (Delete or Comment out these lines)
        # query = f"""
        #     SELECT sensor_id, location, timestamp, temperature, humidity, pressure
        #     FROM sensor_readings
        #     WHERE timestamp >= NOW() - INTERVAL '{hours} hours'
        #     ORDER BY timestamp DESC
        # """
        # df = pd.read_sql(query, conn)

        # NEW FIXED CODE (Paste this instead)
        cutoff_time = datetime.now() - timedelta(hours=hours)
        query = """
            SELECT sensor_id, location, timestamp, temperature, humidity, pressure
            FROM sensor_readings
            WHERE timestamp >= %s
            ORDER BY timestamp DESC
        """
        df = pd.read_sql(query, conn, params=(cutoff_time,))
        
        df['location_clean'] = df['location'].apply(clean_location_name)
        return df
    except Exception as e:
        st.error(f"❌ Query Error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def get_total_record_count():
    """Get total record count from database"""
    conn = get_db_connection()
    if not conn:
        return 0
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sensor_readings")
        total = cursor.fetchone()[0]
        return total
    except Exception as e:
        return 0
    finally:
        conn.close()

def fetch_performance_metrics():
    """Calculate performance metrics"""
    conn = get_db_connection()
    if not conn:
        return {}

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sensor_readings")
        total_records = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM sensor_readings 
            WHERE timestamp >= NOW() - INTERVAL '1 minute'
        """)
        records_last_minute = cursor.fetchone()[0]

        cursor.execute("SELECT MAX(timestamp) FROM sensor_readings")
        latest_time = cursor.fetchone()[0]

        cursor.execute("SELECT pg_size_pretty(pg_database_size('iot_monitoring'))")
        db_size = cursor.fetchone()[0]

        if latest_time:
            latency_seconds = (datetime.now() - latest_time).total_seconds()
            if latency_seconds > 60:
                latency_display = f"{latency_seconds/60:.1f} min ⚠️"
            elif latency_seconds > 10:
                latency_display = f"{latency_seconds:.1f}s ⚠️"
            else:
                latency_display = f"{latency_seconds:.1f}s ✅"
        else:
            latency_display = "N/A"
            latency_seconds = 0

        return {
            'total_records': total_records,
            'ingestion_rate': records_last_minute,
            'latency': latency_seconds,
            'latency_display': latency_display,
            'db_size': db_size
        }
    except Exception as e:
        return {}
    finally:
        conn.close()

def detect_anomalies(df):
    """Detect anomalies using IQR method"""
    if df.empty:
        return df

    df = df.copy()
    Q1_temp = df['temperature'].quantile(0.25)
    Q3_temp = df['temperature'].quantile(0.75)
    IQR_temp = Q3_temp - Q1_temp
    temp_lower = Q1_temp - 1.5 * IQR_temp
    temp_upper = Q3_temp + 1.5 * IQR_temp

    Q1_hum = df['humidity'].quantile(0.25)
    Q3_hum = df['humidity'].quantile(0.75)
    IQR_hum = Q3_hum - Q1_hum
    hum_lower = Q1_hum - 1.5 * IQR_hum
    hum_upper = Q3_hum + 1.5 * IQR_hum

    df['temp_anomaly'] = (df['temperature'] < temp_lower) | (df['temperature'] > temp_upper)
    df['humidity_anomaly'] = (df['humidity'] < hum_lower) | (df['humidity'] > hum_upper)
    df['is_anomaly'] = df['temp_anomaly'] | df['humidity_anomaly']

    return df

def get_detailed_alerts(df):
    """Get detailed alert information"""
    alerts = {
        'high_temp': [],
        'low_temp': [],
        'high_humidity': [],
        'anomalies': []
    }

    if df.empty:
        return alerts

    high_temp = df[df['temperature'] > TEMP_HIGH_THRESHOLD]
    for _, row in high_temp.iterrows():
        alerts['high_temp'].append({
            'sensor': row['sensor_id'],
            'location': row['location_clean'],
            'value': row['temperature'],
            'humidity': row['humidity'],
            'pressure': row['pressure'],
            'time': row['timestamp']
        })

    low_temp = df[df['temperature'] < TEMP_LOW_THRESHOLD]
    for _, row in low_temp.iterrows():
        alerts['low_temp'].append({
            'sensor': row['sensor_id'],
            'location': row['location_clean'],
            'value': row['temperature'],
            'humidity': row['humidity'],
            'pressure': row['pressure'],
            'time': row['timestamp']
        })

    high_humidity = df[df['humidity'] > HUMIDITY_HIGH_THRESHOLD]
    for _, row in high_humidity.iterrows():
        alerts['high_humidity'].append({
            'sensor': row['sensor_id'],
            'location': row['location_clean'],
            'value': row['humidity'],
            'temperature': row['temperature'],
            'pressure': row['pressure'],
            'time': row['timestamp']
        })

    df_with_anomalies = detect_anomalies(df)
    anomalies = df_with_anomalies[df_with_anomalies['is_anomaly']]
    for _, row in anomalies.iterrows():
        alerts['anomalies'].append({
            'sensor': row['sensor_id'],
            'location': row['location_clean'],
            'temp': row['temperature'],
            'humidity': row['humidity'],
            'pressure': row['pressure'],
            'time': row['timestamp']
        })

    return alerts

def get_alert_severity_summary(alerts):
    """Calculate alert severity breakdown"""
    critical = 0
    warning = 0

    for alert in alerts['high_temp']:
        if alert['value'] > 35:
            critical += 1
        else:
            warning += 1

    for alert in alerts['low_temp']:
        if alert['value'] < 10:
            critical += 1
        else:
            warning += 1

    for alert in alerts['high_humidity']:
        if alert['value'] > 90:
            critical += 1
        else:
            warning += 1

    warning += len(alerts['anomalies'])

    return {
        'critical': critical,
        'warning': warning,
        'total': critical + warning
    }

def create_system_architecture_graphviz():
    """Create COMPACT horizontal system architecture diagram using Graphviz"""
    if not GRAPHVIZ_AVAILABLE:
        return None

    dot = graphviz.Digraph(comment='IoT System Architecture')

    # Compact horizontal layout
    dot.attr(rankdir='LR', nodesep='0.3', ranksep='0.4', splines='ortho')
    dot.attr('node', shape='box', style='rounded,filled', fontname='Arial', fontsize='9', 
             width='1.1', height='0.6', margin='0.1,0.05')
    dot.attr('edge', fontname='Arial', fontsize='8', arrowsize='0.7')

    # Nodes with shorter labels
    dot.node('sensors', 'IoT Sensors\n(10 units)', fillcolor='#C8E6C9', color='#388E3C')
    dot.node('mqtt', 'MQTT\nBroker', fillcolor='#FFE0B2', color='#F57C00')
    dot.node('bridge', 'Kafka\nBridge', fillcolor='#E1BEE7', color='#7B1FA2')
    dot.node('kafka', 'Apache\nKafka', fillcolor='#E1BEE7', color='#7B1FA2')
    dot.node('spark', 'Spark\nStreaming', fillcolor='#BBDEFB', color='#1976D2')
    dot.node('postgres', 'PostgreSQL', fillcolor='#B3E5FC', color='#0288D1', shape='cylinder')
    dot.node('dashboard', 'Streamlit\nDashboard', fillcolor='#FFCDD2', color='#D32F2F')

    # Edges
    dot.edge('sensors', 'mqtt', color='#4CAF50', penwidth='1.5')
    dot.edge('mqtt', 'bridge', color='#FF9800', penwidth='1.5')
    dot.edge('bridge', 'kafka', color='#9C27B0', penwidth='1.5')
    dot.edge('kafka', 'spark', color='#9C27B0', penwidth='1.5')
    dot.edge('spark', 'postgres', color='#2196F3', penwidth='1.5')
    dot.edge('postgres', 'dashboard', color='#F44336', penwidth='1.5')

    return dot

# ============================================
# SIDEBAR - UNIFIED DASHBOARD CONTROLS
# ============================================
with st.sidebar:
    st.markdown("## ⚙️ Dashboard Controls")

    # Navigation
    st.markdown("### Navigation")
    page = st.radio(
        "Select Page",
        ["📊 Real-Time Monitoring", "🔬 Advanced Analytics", "⚡ Performance Metrics"],
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Time Window Controls (UNIFIED FOR ALL PAGES)
    st.markdown("### ⏰ Time Window")
    use_date_range = st.checkbox("Use Date Range", value=False)

    if use_date_range:
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=date.today() - timedelta(days=1))
        with col2:
            end_date = st.date_input("End Date", value=date.today())

        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        df_main = fetch_data_by_date_range(start_datetime, end_datetime)
        selected_hours = None
    else:
        time_options = {
            "Last 30 minutes": 0.5,
            "Last 1 hour": 1,
            "Last 2 hours": 2,
            "Last 6 hours": 6,
            "Last 12 hours": 12,
            "Last 24 hours": 24
        }
        selected_time = st.selectbox("Select time range", list(time_options.keys()), index=2)
        selected_hours = time_options[selected_time]
        df_main = fetch_recent_data(selected_hours)

    # Show loaded data info
    if not df_main.empty:
        st.markdown("### 📊 Loaded Data:")
        time_span = (df_main['timestamp'].max() - df_main['timestamp'].min()).total_seconds() / 60
        st.markdown(f"""
        - **Records:** {len(df_main):,}
        - **Time span:** {time_span:.1f} min
        - **From:** {df_main['timestamp'].min().strftime('%Y-%m-%d %H:%M')}
        - **To:** {df_main['timestamp'].max().strftime('%Y-%m-%d %H:%M')}
        """)

    st.markdown("---")

    # Filters
    st.markdown("### 🔍 Filters")

    if not df_main.empty:
        locations = ["All"] + sorted(df_main['location_clean'].unique().tolist())
        selected_location = st.selectbox("Location", locations)

        sensors = ["All"] + sorted(df_main['sensor_id'].unique().tolist())
        selected_sensor = st.selectbox("Sensor ID", sensors)
    else:
        selected_location = "All"
        selected_sensor = "All"

    # Auto-refresh
    auto_refresh = st.checkbox("🔄 Auto-refresh (5s)", value=False)
    if auto_refresh:
        time.sleep(5)
        st.rerun()

    st.markdown("---")

    # Alert Thresholds
    st.markdown("### 🚨 Alert Thresholds")
    st.markdown(f"🔥 High Temp: >{TEMP_HIGH_THRESHOLD}°C")
    st.markdown(f"❄️ Low Temp: <{TEMP_LOW_THRESHOLD}°C")
    st.markdown(f"💧 High Humidity: >{HUMIDITY_HIGH_THRESHOLD}%")

# ============================================
# APPLY FILTERS TO DATA (Location + Sensor + Time)
# ============================================
df_filtered = df_main.copy()

if selected_location != "All" and not df_filtered.empty:
    df_filtered = df_filtered[df_filtered['location_clean'] == selected_location]

if selected_sensor != "All" and not df_filtered.empty:
    df_filtered = df_filtered[df_filtered['sensor_id'] == selected_sensor]

# ============================================
# PAGE: REAL-TIME MONITORING
# ============================================
if page == "📊 Real-Time Monitoring":
    st.title("📊 Real-Time Monitoring")

    st.markdown("""
    This section provides live monitoring of all IoT sensors deployed across the smart city. 
    Data is collected every few seconds from 10 locations and processed in real-time through our 
    MQTT → Kafka → Spark → PostgreSQL pipeline. Use the **sidebar controls** to adjust the time window 
    and filters. All visualizations update automatically based on your selections.
    """)

    if df_filtered.empty:
        st.warning("⚠️ No data available for the selected filters and time range.")
    else:
        # Key Metrics
        st.markdown("### 📈 Key Metrics")
        total_records = get_total_record_count()

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Readings (All Time)", f"{total_records:,}")
        with col2:
            st.metric("Avg Temperature", f"{df_filtered['temperature'].mean():.1f}°C")
        with col3:
            st.metric("Avg Humidity", f"{df_filtered['humidity'].mean():.1f}%")
        with col4:
            st.metric("Active Sensors", df_filtered['sensor_id'].nunique())
        with col5:
            st.metric("Locations", df_filtered['location_clean'].nunique())

        # Alert Summary
        alerts = get_detailed_alerts(df_filtered)
        severity = get_alert_severity_summary(alerts)
        total_alerts = severity['total']
        normal_count = len(df_filtered) - total_alerts

        st.markdown("### 🚨 Alert Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Critical", severity['critical'], delta=None)
        with col2:
            st.metric("Warning", severity['warning'], delta=None)
        with col3:
            st.metric("Normal", normal_count, delta=None)

        # Alert Details with Scrollable Container and Full Details
        if total_alerts > 0:
            with st.expander(f"👁️ View {total_alerts} Alert Details"):
                # High Temperature Alerts
                if alerts['high_temp']:
                    st.markdown("#### 🔥 High Temperature Alerts")
                    high_temp_df = pd.DataFrame(alerts['high_temp'])
                    high_temp_df['value'] = high_temp_df['value'].apply(lambda x: f"{x:.1f}°C")
                    high_temp_df['humidity'] = high_temp_df['humidity'].apply(lambda x: f"{x:.1f}%")
                    high_temp_df['pressure'] = high_temp_df['pressure'].apply(lambda x: f"{x:.1f} hPa")
                    high_temp_df['time'] = pd.to_datetime(high_temp_df['time']).dt.strftime('%Y-%m-%d %H:%M:%S')
                    high_temp_df = high_temp_df.rename(columns={
                        'sensor': 'Sensor ID', 'location': 'Location', 'value': 'Temperature',
                        'humidity': 'Humidity', 'pressure': 'Pressure', 'time': 'Timestamp'
                    })
                    st.dataframe(high_temp_df[['Sensor ID', 'Location', 'Temperature', 'Humidity', 'Pressure', 'Timestamp']], 
                                use_container_width=True, height=200)

                # Low Temperature Alerts
                if alerts['low_temp']:
                    st.markdown("#### ❄️ Low Temperature Alerts")
                    low_temp_df = pd.DataFrame(alerts['low_temp'])
                    low_temp_df['value'] = low_temp_df['value'].apply(lambda x: f"{x:.1f}°C")
                    low_temp_df['humidity'] = low_temp_df['humidity'].apply(lambda x: f"{x:.1f}%")
                    low_temp_df['pressure'] = low_temp_df['pressure'].apply(lambda x: f"{x:.1f} hPa")
                    low_temp_df['time'] = pd.to_datetime(low_temp_df['time']).dt.strftime('%Y-%m-%d %H:%M:%S')
                    low_temp_df = low_temp_df.rename(columns={
                        'sensor': 'Sensor ID', 'location': 'Location', 'value': 'Temperature',
                        'humidity': 'Humidity', 'pressure': 'Pressure', 'time': 'Timestamp'
                    })
                    st.dataframe(low_temp_df[['Sensor ID', 'Location', 'Temperature', 'Humidity', 'Pressure', 'Timestamp']], 
                                use_container_width=True, height=200)

                # High Humidity Alerts
                if alerts['high_humidity']:
                    st.markdown("#### 💧 High Humidity Alerts")
                    high_hum_df = pd.DataFrame(alerts['high_humidity'])
                    high_hum_df['value'] = high_hum_df['value'].apply(lambda x: f"{x:.1f}%")
                    high_hum_df['temperature'] = high_hum_df['temperature'].apply(lambda x: f"{x:.1f}°C")
                    high_hum_df['pressure'] = high_hum_df['pressure'].apply(lambda x: f"{x:.1f} hPa")
                    high_hum_df['time'] = pd.to_datetime(high_hum_df['time']).dt.strftime('%Y-%m-%d %H:%M:%S')
                    high_hum_df = high_hum_df.rename(columns={
                        'sensor': 'Sensor ID', 'location': 'Location', 'value': 'Humidity',
                        'temperature': 'Temperature', 'pressure': 'Pressure', 'time': 'Timestamp'
                    })
                    st.dataframe(high_hum_df[['Sensor ID', 'Location', 'Humidity', 'Temperature', 'Pressure', 'Timestamp']], 
                                use_container_width=True, height=200)

                # Anomalies
                if alerts['anomalies']:
                    st.markdown("#### ⚠️ Statistical Anomalies")
                    anomaly_df = pd.DataFrame(alerts['anomalies'])
                    anomaly_df['temp'] = anomaly_df['temp'].apply(lambda x: f"{x:.1f}°C")
                    anomaly_df['humidity'] = anomaly_df['humidity'].apply(lambda x: f"{x:.1f}%")
                    anomaly_df['pressure'] = anomaly_df['pressure'].apply(lambda x: f"{x:.1f} hPa")
                    anomaly_df['time'] = pd.to_datetime(anomaly_df['time']).dt.strftime('%Y-%m-%d %H:%M:%S')
                    anomaly_df = anomaly_df.rename(columns={
                        'sensor': 'Sensor ID', 'location': 'Location', 'temp': 'Temperature',
                        'humidity': 'Humidity', 'pressure': 'Pressure', 'time': 'Timestamp'
                    })
                    st.dataframe(anomaly_df[['Sensor ID', 'Location', 'Temperature', 'Humidity', 'Pressure', 'Timestamp']], 
                                use_container_width=True, height=200)

        # Temperature Over Time
        st.markdown("### 🌡️ Temperature Over Time")
        df_sorted = df_filtered.sort_values('timestamp')
        fig_temp = px.line(df_sorted, x='timestamp', y='temperature', color='location_clean',
                          labels={'temperature': 'Temperature (°C)', 'timestamp': 'Time', 'location_clean': 'Location'})
        fig_temp.update_layout(height=400, hovermode='x unified')
        st.plotly_chart(fig_temp, use_container_width=True)
        st.caption("📊 Temperature readings from all selected sensors over time. Zoom in by dragging, zoom out by double-clicking.")

        # Humidity Over Time
        st.markdown("### 💧 Humidity Over Time")
        fig_hum = px.line(df_sorted, x='timestamp', y='humidity', color='location_clean',
                         labels={'humidity': 'Humidity (%)', 'timestamp': 'Time', 'location_clean': 'Location'})
        fig_hum.update_layout(height=400, hovermode='x unified')
        st.plotly_chart(fig_hum, use_container_width=True)
        st.caption("💧 Humidity percentage over time. High humidity (>80%) triggers system alerts.")

        # Average by Location
        st.markdown("### 📍 Average Readings by Location")
        avg_by_location = df_filtered.groupby('location_clean').agg({
            'temperature': 'mean',
            'humidity': 'mean'
        }).reset_index()

        fig_loc = go.Figure()
        fig_loc.add_trace(go.Bar(name='Temperature (°C)', x=avg_by_location['location_clean'], 
                                 y=avg_by_location['temperature'], marker_color='#FF6B6B'))
        fig_loc.add_trace(go.Bar(name='Humidity (%)', x=avg_by_location['location_clean'], 
                                 y=avg_by_location['humidity'], marker_color='#4ECDC4'))
        fig_loc.update_layout(barmode='group', height=400, xaxis_title='Location', yaxis_title='Average Value')
        st.plotly_chart(fig_loc, use_container_width=True)

        # Temperature vs Humidity Scatter
        st.markdown("### 🔄 Temperature vs Humidity Relationship")
        fig_scatter = px.scatter(df_filtered, x='temperature', y='humidity', color='location_clean',
                                opacity=0.6, labels={'temperature': 'Temperature (°C)', 'humidity': 'Humidity (%)'})
        fig_scatter.update_layout(height=400)
        st.plotly_chart(fig_scatter, use_container_width=True)

        # Box Plot Distribution
        st.markdown("### 📊 Temperature Distribution by Location")
        fig_box = px.box(df_filtered, x='location_clean', y='temperature', color='location_clean',
                        labels={'location_clean': 'Location', 'temperature': 'Temperature (°C)'})
        fig_box.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_box, use_container_width=True)

        # Recent Readings Table
        st.markdown("### 📋 Recent Sensor Readings")
        col1, col2, col3 = st.columns(3)
        with col1:
            table_location = st.selectbox("Filter by Location", ["All"] + sorted(df_filtered['location_clean'].unique().tolist()), key="table_loc")
        with col2:
            table_sensor = st.selectbox("Filter by Sensor", ["All"] + sorted(df_filtered['sensor_id'].unique().tolist()), key="table_sensor")
        with col3:
            num_rows = st.selectbox("Rows to display", [10, 20, 50, 100], index=1)

        df_table = df_filtered.copy()
        if table_location != "All":
            df_table = df_table[df_table['location_clean'] == table_location]
        if table_sensor != "All":
            df_table = df_table[df_table['sensor_id'] == table_sensor]

        st.dataframe(df_table[['sensor_id', 'location_clean', 'timestamp', 'temperature', 'humidity', 'pressure']].head(num_rows), 
                    use_container_width=True)

# ============================================
# PAGE: ADVANCED ANALYTICS
# ============================================
elif page == "🔬 Advanced Analytics":
    st.title("🔬 Advanced Analytics")

    st.markdown("""
    This section provides deeper insights using statistical methods, machine learning, and geospatial visualization.
    All analytics are computed on the data selected through your **sidebar filters and time window**.
    """)

    if df_filtered.empty:
        st.warning("⚠️ No data available for the selected filters and time range.")
    else:
        # Key Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Records Analyzed", f"{len(df_filtered):,}")
        with col2:
            st.metric("Avg Temperature", f"{df_filtered['temperature'].mean():.1f}°C")
        with col3:
            st.metric("Avg Humidity", f"{df_filtered['humidity'].mean():.1f}%")
        with col4:
            st.metric("Active Sensors", df_filtered['sensor_id'].nunique())

        # Statistical Analysis
        st.markdown("### 📊 Statistical Analysis")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Temperature Statistics**")
            temp_stats = df_filtered['temperature'].describe()
            st.dataframe(temp_stats.round(2))

            std_dev = df_filtered['temperature'].std()
            cv = (std_dev / df_filtered['temperature'].mean()) * 100
            temp_range = df_filtered['temperature'].max() - df_filtered['temperature'].min()

            st.markdown(f"""
            **Key Insights:**
            - Standard deviation: {std_dev:.2f}°C
            - Coefficient of variation: {cv:.2f}%
            - Temperature range: {temp_range:.1f}°C
            """)

        with col2:
            st.markdown("**Temperature Distribution**")
            fig_hist = px.histogram(df_filtered, x='temperature', nbins=30, 
                                   labels={'temperature': 'Temperature (°C)'})
            fig_hist.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig_hist, use_container_width=True)

        # Correlation Analysis
        st.markdown("### 🔗 Correlation Analysis")
        st.markdown("**How are Temperature, Humidity, and Pressure Related?**")

        corr_matrix = df_filtered[['temperature', 'humidity', 'pressure']].corr()

        fig_corr = px.imshow(corr_matrix, text_auto='.2f', aspect='auto',
                            color_continuous_scale='RdBu_r', zmin=-1, zmax=1)
        fig_corr.update_layout(height=350, title='Correlation Matrix')
        st.plotly_chart(fig_corr, use_container_width=True)

        temp_hum_corr = corr_matrix.loc['temperature', 'humidity']
        st.markdown(f"""
        🔥 **Current Findings:** Temperature and Humidity have a correlation of **{temp_hum_corr:.2f}**.
        - Values close to **+1**: Strong positive relationship
        - Values close to **-1**: Strong negative relationship  
        - Values close to **0**: No relationship
        """)

        # Trend Analysis
        st.markdown("### 📈 Trend Analysis")
        st.markdown("**Temperature Trend with Moving Average**")

        df_trend = df_filtered.sort_values('timestamp').copy()
        df_trend['temp_ma'] = df_trend['temperature'].rolling(window=20, min_periods=1).mean()

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(x=df_trend['timestamp'], y=df_trend['temperature'],
                                       mode='lines', name='Raw Temperature', opacity=0.4, line=dict(color='lightblue')))
        fig_trend.add_trace(go.Scatter(x=df_trend['timestamp'], y=df_trend['temp_ma'],
                                       mode='lines', name='Moving Average (20-point)', line=dict(color='red', width=2)))
        fig_trend.update_layout(height=400, xaxis_title='Time', yaxis_title='Temperature (°C)')
        st.plotly_chart(fig_trend, use_container_width=True)

        # Calculate trend direction
        if len(df_trend) > 20:
            recent_trend = df_trend['temp_ma'].iloc[-20:].diff().mean()
            if recent_trend > 0.01:
                trend_text = f"📈 Rising (change of {recent_trend:.3f}°C per reading)"
            elif recent_trend < -0.01:
                trend_text = f"📉 Falling (change of {recent_trend:.3f}°C per reading)"
            else:
                trend_text = "➡️ Stable"
            st.markdown(f"**Current trend:** {trend_text}")

        # ML Predictions
        if ML_AVAILABLE:
            st.markdown("### 🔮 Machine Learning Temperature Predictions")
            st.markdown("Using Linear Regression to predict temperatures 1 hour into the future based on current trends.")

            predictions = []
            for location in df_filtered['location_clean'].unique():
                loc_data = df_filtered[df_filtered['location_clean'] == location].sort_values('timestamp')
                if len(loc_data) >= 10:
                    loc_data = loc_data.copy()
                    loc_data['time_numeric'] = (loc_data['timestamp'] - loc_data['timestamp'].min()).dt.total_seconds()

                    X = loc_data['time_numeric'].values.reshape(-1, 1)
                    y = loc_data['temperature'].values

                    model = LinearRegression()
                    model.fit(X, y)
                    r2 = model.score(X, y)

                    future_time = loc_data['time_numeric'].max() + 3600
                    predicted_temp = model.predict([[future_time]])[0]
                    current_temp = loc_data['temperature'].iloc[-1]

                    predictions.append({
                        'Location': location,
                        'Current Temp': f"{current_temp:.1f}°C",
                        'Predicted (+1hr)': f"{predicted_temp:.1f}°C",
                        'R²': r2
                    })

            if predictions:
                pred_df = pd.DataFrame(predictions)
                avg_r2 = pred_df['R²'].mean()

                st.dataframe(pred_df[['Location', 'Current Temp', 'Predicted (+1hr)']], use_container_width=True)

                if avg_r2 > 0.7:
                    st.success(f"✅ Good model fit (Average R² = {avg_r2:.3f})")
                elif avg_r2 > 0.3:
                    st.warning(f"⚠️ Moderate model fit (Average R² = {avg_r2:.3f})")
                else:
                    st.error(f"❌ Poor model fit (Average R² = {avg_r2:.3f}) - More data needed")

        # Geographic Map
        st.markdown("### 🗺️ Geographic Sensor Map")
        st.markdown("Interactive map showing sensor locations with color-coded status indicators.")

        # Sample coordinates for smart city locations
        location_coords = {
            'Downtown': {'lat': 26.2285, 'lon': 50.5860},
            'Airport': {'lat': 26.2700, 'lon': 50.6337},
            'Industrial Zone': {'lat': 26.1950, 'lon': 50.5500},
            'Residential Area': {'lat': 26.2100, 'lon': 50.6100},
            'City Park': {'lat': 26.2400, 'lon': 50.5700},
            'Harbor': {'lat': 26.2000, 'lon': 50.6200},
            'University Campus': {'lat': 26.2550, 'lon': 50.6000},
            'Shopping Mall': {'lat': 26.2200, 'lon': 50.5950},
            'Highway A1': {'lat': 26.2800, 'lon': 50.5600},
            'Suburb North': {'lat': 26.3000, 'lon': 50.5800}
        }

        map_data = df_filtered.groupby('location_clean').agg({
            'temperature': 'mean',
            'humidity': 'mean',
            'sensor_id': 'count'
        }).reset_index()
        map_data.columns = ['location', 'avg_temp', 'avg_humidity', 'reading_count']

        map_data['lat'] = map_data['location'].map(lambda x: location_coords.get(x, {}).get('lat', 26.2285))
        map_data['lon'] = map_data['location'].map(lambda x: location_coords.get(x, {}).get('lon', 50.5860))

        def get_status_color(temp):
            if temp > TEMP_HIGH_THRESHOLD:
                return 'red'
            elif temp < TEMP_LOW_THRESHOLD:
                return 'blue'
            else:
                return 'green'

        map_data['status'] = map_data['avg_temp'].apply(get_status_color)

        fig_map = px.scatter_mapbox(
            map_data, lat='lat', lon='lon', size='reading_count',
            color='status', color_discrete_map={'green': 'green', 'red': 'red', 'blue': 'blue'},
            hover_name='location',
            hover_data={'avg_temp': ':.1f', 'avg_humidity': ':.1f', 'reading_count': True, 'lat': False, 'lon': False},
            zoom=11, height=500
        )
        fig_map.update_layout(mapbox_style='open-street-map')
        st.plotly_chart(fig_map, use_container_width=True)

        st.markdown("""
        **Map Legend:**
        - 🟢 **Green** = Normal (15-30°C)
        - 🔴 **Red** = High Temperature Alert (>30°C)
        - 🔵 **Blue** = Low Temperature Alert (<15°C)
        """)

# ============================================
# PAGE: PERFORMANCE METRICS
# ============================================
elif page == "⚡ Performance Metrics":
    st.title("⚡ System Performance Metrics")

    st.markdown("""
    This section provides system health monitoring and performance indicators for the entire IoT data pipeline.
    Monitor data ingestion rates, processing latency, database size, and component health.
    """)

    # Performance Indicators
    st.markdown("### 📊 Real-Time Performance Indicators")
    metrics = fetch_performance_metrics()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Records", f"{metrics.get('total_records', 0):,}")
    with col2:
        st.metric("Ingestion Rate", f"{metrics.get('ingestion_rate', 0)}/min")
    with col3:
        st.metric("Processing Latency", metrics.get('latency_display', 'N/A'))
    with col4:
        st.metric("Database Size", metrics.get('db_size', 'N/A'))

    st.caption("⚡ Total Records = all data since system start. Ingestion Rate = new records/minute. Processing Latency = delay between collection and storage.")

    # COMPACT System Architecture with Graphviz
    st.markdown("### 🏗️ System Architecture")

    if GRAPHVIZ_AVAILABLE:
        arch_graph = create_system_architecture_graphviz()
        if arch_graph:
            st.graphviz_chart(arch_graph, use_container_width=True)
    else:
        # Fallback if Graphviz not available
        st.markdown("""
        **Data Pipeline Flow:**

        `IoT Sensors` → `MQTT Broker` → `Kafka Bridge` → `Apache Kafka` → `Spark Streaming` → `PostgreSQL` → `Dashboard`
        """)

    st.caption("🏗️ Data flow: Sensors → MQTT → Kafka → Spark → PostgreSQL → Dashboard")

    # Component Health
    st.markdown("### 📡 Component Health Check")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        conn = get_db_connection()
        if conn:
            st.success("✅ PostgreSQL")
            conn.close()
        else:
            st.error("❌ PostgreSQL")

    with col2:
        st.success("✅ Dashboard")

    with col3:
        if metrics.get('ingestion_rate', 0) > 0:
            st.success("✅ Data Ingestion")
        else:
            st.warning("⚠️ Data Ingestion")

    with col4:
        latency = metrics.get('latency', 999)
        if latency < 10:
            st.success("✅ Low Latency")
        elif latency < 60:
            st.warning("⚠️ Check Latency")
        else:
            st.error("❌ High Latency")

    # Pipeline Details
    st.markdown("### 📋 Pipeline Components")

    pipeline_data = {
        'Component': ['IoT Sensors', 'MQTT Broker', 'Kafka Bridge', 'Apache Kafka', 'Spark Streaming', 'PostgreSQL', 'Streamlit'],
        'Technology': ['mqtt_producer.py', 'Mosquitto', 'mqtt_to_kafka.py', 'Apache Kafka', 'PySpark', 'PostgreSQL 15', 'Streamlit'],
        'Port': ['N/A', '1883', 'N/A', '9092', '4040 (UI)', '5432', '8501'],
        'Function': ['Generate sensor data', 'Message routing', 'Protocol translation', 'Distributed streaming', 'Real-time processing', 'Data storage', 'Visualization & ML']
    }

    st.dataframe(pd.DataFrame(pipeline_data), use_container_width=True, hide_index=True)

# Footer
st.markdown("---")
st.markdown("🌡️ **IoT Monitoring Dashboard** | Smart City Sensor Network | Real-time Analytics")
