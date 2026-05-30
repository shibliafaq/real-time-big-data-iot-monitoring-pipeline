"""
IoT Smart City Monitoring Dashboard — Demo Version
===================================================
Production version runs: MQTT → Kafka → Spark → PostgreSQL → Streamlit
Demo version replaces the database layer with realistic simulated data.
All features, visualizations, and ML are identical to production.

Author: Shibli Afaq | KFUPM MSc Smart & Sustainable Cities
Course: ICS 574 — Big Data Analytics
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import time

try:
    from sklearn.linear_model import LinearRegression
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

try:
    import graphviz
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IoT Smart City Dashboard",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────────────────────
# ALERT THRESHOLDS  (same as production)
# ─────────────────────────────────────────────────────────────────────────────
TEMP_HIGH_THRESHOLD  = 30.0   # °C  — triggers high-temp alert
TEMP_LOW_THRESHOLD   = 15.0   # °C  — triggers low-temp alert
HUMIDITY_HIGH_THRESHOLD = 80.0

# ─────────────────────────────────────────────────────────────────────────────
# SENSOR METADATA  (10 Dammam / Al-Khobar smart city locations)
# ─────────────────────────────────────────────────────────────────────────────
SENSORS = {
    "sensor_001": {"location": "downtown",         "lat": 26.4282, "lon": 50.1069, "base_temp": 38.0, "base_hum": 45},
    "sensor_002": {"location": "airport",           "lat": 26.4712, "lon": 49.7980, "base_temp": 40.0, "base_hum": 35},
    "sensor_003": {"location": "industrial_zone",   "lat": 26.2950, "lon": 50.1800, "base_temp": 43.5, "base_hum": 25},
    "sensor_004": {"location": "residential_area",  "lat": 26.3900, "lon": 50.1900, "base_temp": 36.0, "base_hum": 52},
    "sensor_005": {"location": "city_park",         "lat": 26.4100, "lon": 50.0900, "base_temp": 32.0, "base_hum": 58},
    "sensor_006": {"location": "harbor",            "lat": 26.3300, "lon": 50.2100, "base_temp": 33.5, "base_hum": 72},
    "sensor_007": {"location": "university_campus", "lat": 26.3070, "lon": 50.1500, "base_temp": 34.5, "base_hum": 48},
    "sensor_008": {"location": "shopping_mall",     "lat": 26.3680, "lon": 50.1650, "base_temp": 37.0, "base_hum": 42},
    "sensor_009": {"location": "highway_a1",        "lat": 26.4500, "lon": 50.0700, "base_temp": 41.0, "base_hum": 30},
    "sensor_010": {"location": "suburb_north",      "lat": 26.4800, "lon": 50.1200, "base_temp": 35.5, "base_hum": 46},
}

# ─────────────────────────────────────────────────────────────────────────────
# DATA GENERATION  (called once; cached for the session)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data
def generate_base_data() -> pd.DataFrame:
    """
    Generate 7 days of realistic smart-city IoT readings.
    Replaces the live PostgreSQL query in production.
    Includes diurnal cycles, location-specific baselines, and
    injected anomalies so every dashboard feature fires correctly.
    """
    rng = np.random.default_rng(seed=42)
    end_time   = datetime.now().replace(second=0, microsecond=0)
    start_time = end_time - timedelta(days=7)
    timestamps = pd.date_range(start=start_time, end=end_time, freq="2min")

    records = []
    for sensor_id, meta in SENSORS.items():
        n = len(timestamps)
        hours = np.array([ts.hour + ts.minute / 60 for ts in timestamps])

        # Diurnal temp swing: +8°C peak at 14:00, −4°C trough at 04:00
        diurnal = 8.0 * np.sin((hours - 6.0) * np.pi / 12.0)
        diurnal[hours < 6]  = -4.0
        diurnal[hours > 18] = -4.0

        temp     = meta["base_temp"] + diurnal + rng.normal(0, 1.5, n)
        humidity = meta["base_hum"]            + rng.normal(0, 5.0, n)
        pressure = 1010.0                      + rng.normal(0, 3.0, n)
        humidity = np.clip(humidity, 10, 98)

        # Inject a handful of anomalies (5 % of readings per sensor)
        anomaly_idx = rng.choice(n, size=max(1, n // 20), replace=False)
        temp[anomaly_idx]     += rng.choice([-15, +15], size=len(anomaly_idx))
        humidity[anomaly_idx] += rng.choice([-30, +25], size=len(anomaly_idx))
        humidity = np.clip(humidity, 10, 98)

        for i, ts in enumerate(timestamps):
            records.append({
                "sensor_id":    sensor_id,
                "location":     meta["location"],
                "timestamp":    ts,
                "temperature":  round(float(temp[i]),     2),
                "humidity":     round(float(humidity[i]), 2),
                "pressure":     round(float(pressure[i]), 2),
                "lat":          meta["lat"],
                "lon":          meta["lon"],
            })

    df = pd.DataFrame(records)
    df["location_clean"] = df["location"].apply(
        lambda x: x.replace("_", " ").title()
    )
    return df


# ─────────────────────────────────────────────────────────────────────────────
# FILTERING HELPERS  (replace DB queries)
# ─────────────────────────────────────────────────────────────────────────────
def fetch_recent_data(hours: float) -> pd.DataFrame:
    df  = generate_base_data()
    cutoff = datetime.now() - timedelta(hours=hours)
    return df[df["timestamp"] >= cutoff].copy()


def fetch_data_by_date_range(start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
    df = generate_base_data()
    return df[(df["timestamp"] >= start_dt) & (df["timestamp"] <= end_dt)].copy()


def get_total_record_count() -> int:
    return len(generate_base_data())


# ─────────────────────────────────────────────────────────────────────────────
# SIMULATED PERFORMANCE METRICS
# ─────────────────────────────────────────────────────────────────────────────
def fetch_performance_metrics() -> dict:
    """
    In production these come from live Kafka/Spark/PostgreSQL telemetry.
    Here we return plausible values drawn from the generated dataset.
    """
    total    = get_total_record_count()
    # Simulate small per-refresh variation so metrics 'feel' live
    jitter   = int(np.random.randint(28, 34))
    latency  = round(np.random.uniform(2.8, 4.5), 1)

    return {
        "total_records":    total,
        "ingestion_rate":   jitter,
        "latency":          latency,
        "latency_display":  f"{latency}s ✅",
        "db_size":          "~52 MB",
    }


# ─────────────────────────────────────────────────────────────────────────────
# ALERT DETECTION  (unchanged from production)
# ─────────────────────────────────────────────────────────────────────────────
def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    for col, label in [("temperature", "temp"), ("humidity", "humidity")]:
        Q1, Q3  = df[col].quantile([0.25, 0.75])
        IQR     = Q3 - Q1
        df[f"{label}_anomaly"] = (df[col] < Q1 - 1.5*IQR) | (df[col] > Q3 + 1.5*IQR)
    df["is_anomaly"] = df["temp_anomaly"] | df["humidity_anomaly"]
    return df


def get_detailed_alerts(df: pd.DataFrame) -> dict:
    alerts = {"high_temp": [], "low_temp": [], "high_humidity": [], "anomalies": []}
    if df.empty:
        return alerts

    for _, row in df[df["temperature"] > TEMP_HIGH_THRESHOLD].iterrows():
        alerts["high_temp"].append({"sensor": row["sensor_id"], "location": row["location_clean"],
            "value": row["temperature"], "humidity": row["humidity"],
            "pressure": row["pressure"], "time": row["timestamp"]})

    for _, row in df[df["temperature"] < TEMP_LOW_THRESHOLD].iterrows():
        alerts["low_temp"].append({"sensor": row["sensor_id"], "location": row["location_clean"],
            "value": row["temperature"], "humidity": row["humidity"],
            "pressure": row["pressure"], "time": row["timestamp"]})

    for _, row in df[df["humidity"] > HUMIDITY_HIGH_THRESHOLD].iterrows():
        alerts["high_humidity"].append({"sensor": row["sensor_id"], "location": row["location_clean"],
            "value": row["humidity"], "temperature": row["temperature"],
            "pressure": row["pressure"], "time": row["timestamp"]})

    df_anom = detect_anomalies(df)
    for _, row in df_anom[df_anom["is_anomaly"]].iterrows():
        alerts["anomalies"].append({"sensor": row["sensor_id"], "location": row["location_clean"],
            "temp": row["temperature"], "humidity": row["humidity"],
            "pressure": row["pressure"], "time": row["timestamp"]})

    return alerts


def get_alert_severity_summary(alerts: dict) -> dict:
    critical = sum(1 for a in alerts["high_temp"]      if a["value"] > 35)
    critical += sum(1 for a in alerts["low_temp"]      if a["value"] < 10)
    critical += sum(1 for a in alerts["high_humidity"] if a["value"] > 90)
    warning  = len(alerts["high_temp"])  - sum(1 for a in alerts["high_temp"]  if a["value"] > 35)
    warning += len(alerts["low_temp"])   - sum(1 for a in alerts["low_temp"]   if a["value"] < 10)
    warning += len(alerts["high_humidity"]) - sum(1 for a in alerts["high_humidity"] if a["value"] > 90)
    warning += len(alerts["anomalies"])
    return {"critical": critical, "warning": warning, "total": critical + warning}


# ─────────────────────────────────────────────────────────────────────────────
# ARCHITECTURE DIAGRAM  (graphviz — unchanged from production)
# ─────────────────────────────────────────────────────────────────────────────
def create_architecture_diagram():
    if not GRAPHVIZ_AVAILABLE:
        return None
    dot = graphviz.Digraph()
    dot.attr(rankdir="LR", nodesep="0.3", ranksep="0.4", splines="ortho")
    dot.attr("node", shape="box", style="rounded,filled",
             fontname="Arial", fontsize="9", width="1.1", height="0.6", margin="0.1,0.05")
    dot.attr("edge", fontname="Arial", fontsize="8", arrowsize="0.7")
    dot.node("sensors",   "IoT Sensors\n(10 units)",   fillcolor="#C8E6C9", color="#388E3C")
    dot.node("mqtt",      "MQTT\nBroker",               fillcolor="#FFE0B2", color="#F57C00")
    dot.node("bridge",    "Kafka\nBridge",              fillcolor="#E1BEE7", color="#7B1FA2")
    dot.node("kafka",     "Apache\nKafka",              fillcolor="#E1BEE7", color="#7B1FA2")
    dot.node("spark",     "Spark\nStreaming",           fillcolor="#BBDEFB", color="#1976D2")
    dot.node("postgres",  "PostgreSQL",                 fillcolor="#B3E5FC", color="#0288D1", shape="cylinder")
    dot.node("dashboard", "Streamlit\nDashboard",       fillcolor="#FFCDD2", color="#D32F2F")
    for a, b, c in [("sensors","mqtt","#4CAF50"), ("mqtt","bridge","#FF9800"),
                    ("bridge","kafka","#9C27B0"), ("kafka","spark","#9C27B0"),
                    ("spark","postgres","#2196F3"), ("postgres","dashboard","#F44336")]:
        dot.edge(a, b, color=c, penwidth="1.5")
    return dot


# ─────────────────────────────────────────────────────────────────────────────
# DEMO BANNER
# ─────────────────────────────────────────────────────────────────────────────
st.info(
    "**Demo mode** — running on 7 days of simulated data. "
    "Production version ingests live sensor data via MQTT → Kafka → Spark → PostgreSQL. "
    "See the [GitHub repo](https://github.com/shibliafaq/real-time-big-data-iot-monitoring-pipeline) "
    "for the full Docker-based production setup.",
    icon="ℹ️",
)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Dashboard Controls")
    st.markdown("### Navigation")
    page = st.radio(
        "Select Page",
        ["📊 Real-Time Monitoring", "🔬 Advanced Analytics", "⚡ Performance Metrics"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown("### ⏰ Time Window")
    use_date_range = st.checkbox("Use Date Range", value=False)

    if use_date_range:
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start", value=date.today() - timedelta(days=1))
        with col2:
            end_date   = st.date_input("End",   value=date.today())
        df_main = fetch_data_by_date_range(
            datetime.combine(start_date, datetime.min.time()),
            datetime.combine(end_date,   datetime.max.time()),
        )
    else:
        time_options = {
            "Last 30 minutes": 0.5,
            "Last 1 hour": 1,
            "Last 2 hours": 2,
            "Last 6 hours": 6,
            "Last 12 hours": 12,
            "Last 24 hours": 24,
        }
        selected_time = st.selectbox("Select time range", list(time_options.keys()), index=2)
        df_main = fetch_recent_data(time_options[selected_time])

    if not df_main.empty:
        span_min = (df_main["timestamp"].max() - df_main["timestamp"].min()).total_seconds() / 60
        st.markdown("### 📊 Loaded Data")
        st.markdown(
            f"- **Records:** {len(df_main):,}\n"
            f"- **Time span:** {span_min:.0f} min\n"
            f"- **From:** {df_main['timestamp'].min().strftime('%Y-%m-%d %H:%M')}\n"
            f"- **To:** {df_main['timestamp'].max().strftime('%Y-%m-%d %H:%M')}"
        )

    st.markdown("---")
    st.markdown("### 🔍 Filters")
    if not df_main.empty:
        locations     = ["All"] + sorted(df_main["location_clean"].unique().tolist())
        sensors_list  = ["All"] + sorted(df_main["sensor_id"].unique().tolist())
        sel_location  = st.selectbox("Location", locations)
        sel_sensor    = st.selectbox("Sensor ID", sensors_list)
    else:
        sel_location = sel_sensor = "All"

    auto_refresh = st.checkbox("🔄 Auto-refresh (5 s)", value=False)
    if auto_refresh:
        time.sleep(5)
        st.rerun()

    st.markdown("---")
    st.markdown("### 🚨 Alert Thresholds")
    st.markdown(
        f"🔥 High Temp: > {TEMP_HIGH_THRESHOLD}°C\n\n"
        f"❄️ Low Temp: < {TEMP_LOW_THRESHOLD}°C\n\n"
        f"💧 High Humidity: > {HUMIDITY_HIGH_THRESHOLD}%"
    )

# ─────────────────────────────────────────────────────────────────────────────
# APPLY FILTERS
# ─────────────────────────────────────────────────────────────────────────────
df_filtered = df_main.copy()
if sel_location != "All" and not df_filtered.empty:
    df_filtered = df_filtered[df_filtered["location_clean"] == sel_location]
if sel_sensor != "All" and not df_filtered.empty:
    df_filtered = df_filtered[df_filtered["sensor_id"] == sel_sensor]


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 1 — REAL-TIME MONITORING
# ═════════════════════════════════════════════════════════════════════════════
if page == "📊 Real-Time Monitoring":
    st.title("📊 Real-Time Monitoring")
    st.markdown(
        "Live metrics from 10 smart-city sensors across Dammam / Al-Khobar. "
        "Use the sidebar to adjust the time window and location filters. "
        "In production, data flows every ~2 seconds from physical IoT nodes "
        "via MQTT → Kafka → Spark → PostgreSQL."
    )

    if df_filtered.empty:
        st.warning("⚠️ No data for the selected filters and time range.")
        st.stop()

    # KPI row
    st.markdown("### 📈 Key Metrics")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Readings (All Time)", f"{get_total_record_count():,}")
    c2.metric("Avg Temperature",  f"{df_filtered['temperature'].mean():.1f}°C")
    c3.metric("Avg Humidity",     f"{df_filtered['humidity'].mean():.1f}%")
    c4.metric("Active Sensors",   df_filtered["sensor_id"].nunique())
    c5.metric("Locations",        df_filtered["location_clean"].nunique())

    # Alert summary
    alerts   = get_detailed_alerts(df_filtered)
    severity = get_alert_severity_summary(alerts)
    st.markdown("### 🚨 Alert Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Critical", severity["critical"])
    c2.metric("Warning",  severity["warning"])
    c3.metric("Normal",   len(df_filtered) - severity["total"])

    if severity["total"] > 0:
        with st.expander(f"👁️ View {severity['total']} Alert Details"):
            for key, label, col in [
                ("high_temp",     "🔥 High Temperature Alerts",  "value"),
                ("low_temp",      "❄️ Low Temperature Alerts",   "value"),
                ("high_humidity", "💧 High Humidity Alerts",     "value"),
            ]:
                if alerts[key]:
                    st.markdown(f"#### {label}")
                    tmp = pd.DataFrame(alerts[key])
                    tmp["time"] = pd.to_datetime(tmp["time"]).dt.strftime("%Y-%m-%d %H:%M:%S")
                    st.dataframe(tmp, use_container_width=True, height=200)

            if alerts["anomalies"]:
                st.markdown("#### ⚠️ Statistical Anomalies (IQR method)")
                tmp = pd.DataFrame(alerts["anomalies"])
                tmp["time"] = pd.to_datetime(tmp["time"]).dt.strftime("%Y-%m-%d %H:%M:%S")
                st.dataframe(tmp, use_container_width=True, height=200)

    # Time-series charts
    df_s = df_filtered.sort_values("timestamp")

    st.markdown("### 🌡️ Temperature Over Time")
    fig = px.line(df_s, x="timestamp", y="temperature", color="location_clean",
                  labels={"temperature": "Temperature (°C)", "timestamp": "Time",
                          "location_clean": "Location"})
    fig.update_layout(height=400, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Zoom by dragging; reset with double-click.")

    st.markdown("### 💧 Humidity Over Time")
    fig = px.line(df_s, x="timestamp", y="humidity", color="location_clean",
                  labels={"humidity": "Humidity (%)", "timestamp": "Time",
                          "location_clean": "Location"})
    fig.update_layout(height=400, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 📍 Average Readings by Location")
    avg = df_filtered.groupby("location_clean")[["temperature","humidity"]].mean().reset_index()
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Temperature (°C)", x=avg["location_clean"],
                         y=avg["temperature"], marker_color="#FF6B6B"))
    fig.add_trace(go.Bar(name="Humidity (%)",     x=avg["location_clean"],
                         y=avg["humidity"],      marker_color="#4ECDC4"))
    fig.update_layout(barmode="group", height=400,
                      xaxis_title="Location", yaxis_title="Average Value")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 🔄 Temperature vs Humidity")
    fig = px.scatter(df_filtered, x="temperature", y="humidity", color="location_clean",
                     opacity=0.5, labels={"temperature":"Temperature (°C)","humidity":"Humidity (%)"})
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 📊 Temperature Distribution by Location")
    fig = px.box(df_filtered, x="location_clean", y="temperature", color="location_clean",
                 labels={"location_clean":"Location","temperature":"Temperature (°C)"})
    fig.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 📋 Recent Sensor Readings")
    c1, c2, c3 = st.columns(3)
    t_loc = c1.selectbox("Filter", ["All"]+sorted(df_filtered["location_clean"].unique().tolist()), key="tl")
    t_sen = c2.selectbox("Sensor", ["All"]+sorted(df_filtered["sensor_id"].unique().tolist()),    key="ts")
    n_rows = c3.selectbox("Rows", [10,20,50,100], index=1)
    view = df_filtered.copy()
    if t_loc != "All": view = view[view["location_clean"]==t_loc]
    if t_sen != "All": view = view[view["sensor_id"]==t_sen]
    st.dataframe(
        view[["sensor_id","location_clean","timestamp","temperature","humidity","pressure"]].head(n_rows),
        use_container_width=True,
    )


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 2 — ADVANCED ANALYTICS
# ═════════════════════════════════════════════════════════════════════════════
elif page == "🔬 Advanced Analytics":
    st.title("🔬 Advanced Analytics")
    st.markdown(
        "Statistical analysis, correlation, ML temperature forecasting, and geospatial "
        "visualisation — all computed on the time window selected in the sidebar."
    )

    if df_filtered.empty:
        st.warning("⚠️ No data for the selected filters and time range.")
        st.stop()

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Records Analysed", f"{len(df_filtered):,}")
    c2.metric("Avg Temperature",  f"{df_filtered['temperature'].mean():.1f}°C")
    c3.metric("Avg Humidity",     f"{df_filtered['humidity'].mean():.1f}%")
    c4.metric("Active Sensors",   df_filtered["sensor_id"].nunique())

    # Statistics
    st.markdown("### 📊 Statistical Analysis")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Temperature statistics**")
        st.dataframe(df_filtered["temperature"].describe().round(2))
        std  = df_filtered["temperature"].std()
        mean = df_filtered["temperature"].mean()
        rng  = df_filtered["temperature"].max() - df_filtered["temperature"].min()
        st.markdown(f"- Std dev: **{std:.2f}°C** | CV: **{std/mean*100:.1f}%** | Range: **{rng:.1f}°C**")
    with c2:
        fig = px.histogram(df_filtered, x="temperature", nbins=30,
                           labels={"temperature":"Temperature (°C)"})
        fig.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # Correlation
    st.markdown("### 🔗 Correlation Matrix")
    corr = df_filtered[["temperature","humidity","pressure"]].corr()
    fig  = px.imshow(corr, text_auto=".2f", aspect="auto",
                     color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)
    r = corr.loc["temperature","humidity"]
    st.markdown(
        f"Temperature–Humidity correlation: **{r:.2f}** "
        f"({'negative' if r < 0 else 'positive'} relationship — "
        f"{'as expected in hot-arid climate' if r < -0.2 else 'typical for this dataset'})."
    )

    # Trend
    st.markdown("### 📈 Trend Analysis — Moving Average")
    df_t = df_filtered.sort_values("timestamp").copy()
    df_t["ma20"] = df_t["temperature"].rolling(20, min_periods=1).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_t["timestamp"], y=df_t["temperature"],
                             mode="lines", name="Raw", opacity=0.3,
                             line=dict(color="lightblue")))
    fig.add_trace(go.Scatter(x=df_t["timestamp"], y=df_t["ma20"],
                             mode="lines", name="20-pt Moving Avg",
                             line=dict(color="red", width=2)))
    fig.update_layout(height=400, xaxis_title="Time", yaxis_title="Temperature (°C)")
    st.plotly_chart(fig, use_container_width=True)

    if len(df_t) > 20:
        slope = df_t["ma20"].iloc[-20:].diff().mean()
        direction = "📈 Rising" if slope > 0.01 else ("📉 Falling" if slope < -0.01 else "➡️ Stable")
        st.markdown(f"**Current trend:** {direction} ({slope:+.3f}°C per reading)")

    # ML predictions
    if ML_AVAILABLE:
        st.markdown("### 🔮 ML Temperature Forecast (+1 hour)")
        st.markdown("Linear regression trained on the selected time window; extrapolated 60 minutes ahead.")
        preds = []
        for loc in df_filtered["location_clean"].unique():
            sub = df_filtered[df_filtered["location_clean"]==loc].sort_values("timestamp")
            if len(sub) < 10:
                continue
            sub = sub.copy()
            sub["t_num"] = (sub["timestamp"] - sub["timestamp"].min()).dt.total_seconds()
            X, y = sub["t_num"].values.reshape(-1,1), sub["temperature"].values
            m = LinearRegression().fit(X, y)
            r2   = m.score(X, y)
            pred = m.predict([[sub["t_num"].max() + 3600]])[0]
            preds.append({"Location": loc,
                          "Current (°C)": f"{sub['temperature'].iloc[-1]:.1f}",
                          "Forecast +1 hr (°C)": f"{pred:.1f}",
                          "R²": round(r2, 3)})
        if preds:
            pred_df = pd.DataFrame(preds)
            st.dataframe(pred_df, use_container_width=True, hide_index=True)
            avg_r2 = pred_df["R²"].mean()
            if avg_r2 > 0.7:
                st.success(f"Good model fit — average R² = {avg_r2:.3f}")
            elif avg_r2 > 0.3:
                st.warning(f"Moderate model fit — average R² = {avg_r2:.3f}")
            else:
                st.error(f"Low model fit — average R² = {avg_r2:.3f}. Widen the time window for better results.")

    # Geospatial map
    st.markdown("### 🗺️ Sensor Locations — Heat Status")
    map_df = (
        df_filtered
        .groupby("location_clean")
        .agg(avg_temp=("temperature","mean"),
             avg_hum=("humidity","mean"),
             count=("sensor_id","count"),
             lat=("lat","first"),
             lon=("lon","first"))
        .reset_index()
    )
    map_df["status"] = map_df["avg_temp"].apply(
        lambda t: "High Temp" if t > TEMP_HIGH_THRESHOLD else ("Low Temp" if t < TEMP_LOW_THRESHOLD else "Normal")
    )
    fig = px.scatter_mapbox(
        map_df, lat="lat", lon="lon", size="count",
        color="status",
        color_discrete_map={"Normal":"green","High Temp":"red","Low Temp":"blue"},
        hover_name="location_clean",
        hover_data={"avg_temp":":.1f","avg_hum":":.1f","count":True,"lat":False,"lon":False},
        zoom=10, height=520,
    )
    fig.update_layout(mapbox_style="open-street-map")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("🟢 Normal (15–30°C) &nbsp;&nbsp; 🔴 High Temp (>30°C) &nbsp;&nbsp; 🔵 Low Temp (<15°C)")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 3 — PERFORMANCE METRICS
# ═════════════════════════════════════════════════════════════════════════════
elif page == "⚡ Performance Metrics":
    st.title("⚡ System Performance Metrics")
    st.markdown(
        "Pipeline health and throughput indicators. "
        "In production, these are pulled live from Kafka consumer-group offsets, "
        "Spark Streaming UI, and PostgreSQL system tables."
    )

    m = fetch_performance_metrics()
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Records",       f"{m['total_records']:,}")
    c2.metric("Ingestion Rate",      f"{m['ingestion_rate']}/min")
    c3.metric("Processing Latency",  m["latency_display"])
    c4.metric("Database Size",       m["db_size"])
    st.caption("Simulated telemetry — values derived from the generated dataset.")

    # Architecture diagram
    st.markdown("### 🏗️ Pipeline Architecture")
    if GRAPHVIZ_AVAILABLE:
        g = create_architecture_diagram()
        if g:
            st.graphviz_chart(g, use_container_width=True)
    else:
        st.markdown(
            "`IoT Sensors` → `MQTT Broker (Mosquitto)` → `Kafka Bridge` "
            "→ `Apache Kafka` → `Spark Streaming` → `PostgreSQL` → `Streamlit`"
        )

    # Component health
    st.markdown("### 📡 Component Health")
    c1,c2,c3,c4 = st.columns(4)
    c1.success("✅ PostgreSQL\n(simulated)")
    c2.success("✅ Dashboard")
    c3.success("✅ Data Ingestion")
    c4.success("✅ Low Latency")

    # Pipeline table
    st.markdown("### 📋 Component Details")
    pipeline = pd.DataFrame([
        ["IoT Sensors (10)",  "mqtt_producer.py",      "—",    "Simulate & publish sensor readings"],
        ["MQTT Broker",       "Mosquitto",              "1883", "Lightweight IoT message routing"],
        ["Kafka Bridge",      "mqtt_to_kafka.py",       "—",    "MQTT → Kafka protocol translation"],
        ["Message Broker",    "Apache Kafka 3.x",       "9092", "Distributed streaming & buffering"],
        ["Stream Processing", "PySpark (Structured)",   "4040", "5-min window aggregations"],
        ["Database",          "PostgreSQL 15",          "5432", "Raw readings + aggregates"],
        ["Dashboard",         "Streamlit",              "8501", "Visualisation, analytics & ML"],
    ], columns=["Component","Technology","Port","Function"])
    st.dataframe(pipeline, use_container_width=True, hide_index=True)

    st.markdown("### 📊 Performance Benchmarks")
    bench = pd.DataFrame([
        ["Sensor count",       "10"],
        ["Generation rate",    "~30 readings / min"],
        ["Aggregation window", "5 minutes"],
        ["Dashboard refresh",  "5 seconds (auto-refresh)"],
        ["Processing latency", "< 10 seconds end-to-end"],
        ["ML model",           "Linear Regression (scikit-learn)"],
        ["Anomaly detection",  "IQR method (1.5 × IQR)"],
    ], columns=["Metric","Value"])
    st.dataframe(bench, use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "🌡️ **IoT Smart City Monitoring Dashboard** · "
    "Shibli Afaq · KFUPM MSc Smart & Sustainable Cities · ICS 574 Big Data Analytics"
)
