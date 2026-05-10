import streamlit as st
import paho.mqtt.client as mqtt
import pandas as pd
import plotly.graph_objects as go
import json
import time
from datetime import datetime

# ==========================================
# KONFIGURASI MQTT
# ==========================================
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "rianyuliawan/sensor_data"


# ==========================================
# PENYIMPANAN DATA ANTI-GAGAL (THREAD-SAFE)
# ==========================================
@st.cache_resource
def get_data_store():
    return {
        "latest": {
            "ac_voltage": 0.0,
            "ldr_adc": 0,
            "light_status": "MENUNGGU...",
            "hall_voltage": 0.0,
            "magnet_strength": 0.0,
            "magnet_direction": "MENUNGGU...",
            "timestamp": 0,
        }
    }


data_store = get_data_store()

if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(
        columns=["time", "ac_voltage", "ldr_adc", "hall_voltage", "magnet_strength"]
    )

if "last_update" not in st.session_state:
    st.session_state.last_update = 0


# ==========================================
# FUNGSI MQTT CALLBACK
# ==========================================
def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8")
        data = json.loads(payload)
        data["timestamp"] = time.time()
        data_store["latest"] = data
    except Exception as e:
        pass  # Disembunyikan agar log terminal tidak penuh


@st.cache_resource
def init_mqtt():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_start()
    return client


mqtt_client = init_mqtt()


# ==========================================
# FUNGSI GAUGE METER BLYNK
# ==========================================
def create_gauge(value, min_val, max_val, unit=""):
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": unit, "font": {"size": 40}},
            gauge={
                "axis": {"range": [min_val, max_val], "tickwidth": 1},
                "bar": {"color": "#ccff00"},
                "bgcolor": "white",
                "borderwidth": 2,
                "bordercolor": "#e6e6e6",
                "steps": [{"range": [min_val, max_val], "color": "#f4f4f4"}],
            },
        )
    )
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=20, b=20))
    return fig


# ==========================================
# UI STREAMLIT (DENGAN CUSTOM HEADER)
# ==========================================
st.set_page_config(
    page_title="Dashboard AIoT - Rian Yuliawan", layout="centered", page_icon="⚡"
)

# ------------------------------------------------
# HEADER UI/UX KUSTOM
# ------------------------------------------------
st.markdown(
    """
    <div style='text-align: center; padding: 25px; background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%); border-radius: 15px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
        <h1 style='color: white; margin-bottom: 5px; font-size: 32px;'>⚡ Dashboard Monitoring</h1>
        <p style='color: #ecf0f1; font-size: 18px; margin-top: 0px;'>Sistem ZMPT101B, LDR, dan OH49E</p>
        <hr style='border: 1px solid #7f8c8d; margin: 15px 0;'>
    </div>
""",
    unsafe_allow_html=True,
)

# Ambil data dari kotak surat global
data = data_store["latest"]

# Update histori jika ada timestamp baru
if data["timestamp"] > st.session_state.last_update:
    new_row = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "ac_voltage": data["ac_voltage"],
        "ldr_adc": data["ldr_adc"],
        "hall_voltage": data["hall_voltage"],
        "magnet_strength": data["magnet_strength"],
    }

    st.session_state.history = pd.concat(
        [st.session_state.history, pd.DataFrame([new_row])], ignore_index=True
    )

    if len(st.session_state.history) > 50:
        st.session_state.history = st.session_state.history.iloc[-50:]

    st.session_state.last_update = data["timestamp"]

df_chart = st.session_state.history.copy()
if not df_chart.empty:
    df_chart.set_index("time", inplace=True)

# 1. AC Voltage Monitor
with st.container(border=True):
    st.markdown("#### AC Voltage Monitor (Sensor ZMPT101B)")
    st.plotly_chart(
        create_gauge(data["ac_voltage"], 0, 250, "V"), width="stretch", key="g_ac"
    )

# 2. Chart AC Voltage
with st.container(border=True):
    st.markdown("#### Chart AC Voltage (Sensor ZMPT101B)")
    if len(df_chart) < 2:
        st.info(
            "⏳ Menunggu minimal 2 data dari Wokwi untuk menggambar grafik garis..."
        )
    else:
        st.line_chart(df_chart["ac_voltage"], color="#e68a73", width="stretch")

# 3. Light Intensity
with st.container(border=True):
    st.markdown("#### Light Intensity (Sensor LDR)")
    st.plotly_chart(
        create_gauge(data["ldr_adc"], 0, 4095), width="stretch", key="g_ldr"
    )

# 4. Chart Light Intensity
with st.container(border=True):
    st.markdown("#### Chart Light Intensity (Sensor LDR)")
    if len(df_chart) < 2:
        st.info(
            "⏳ Menunggu minimal 2 data dari Wokwi untuk menggambar grafik garis..."
        )
    else:
        st.line_chart(df_chart["ldr_adc"], color="#6b7c8c", width="stretch")

# 5. Room Light Status
with st.container(border=True):
    st.markdown("#### Room Light Status")
    # Warna teks dihapus agar otomatis terang di Dark Mode
    st.markdown(
        f"<h1 style='font-weight:normal;'>{data['light_status']}</h1>",
        unsafe_allow_html=True,
    )

# 6. Hall Sensor Voltage
with st.container(border=True):
    st.markdown("#### Hall Sensor Voltage (Sensor OH49E)")
    st.plotly_chart(
        create_gauge(data["hall_voltage"], 0, 4, "V"), width="stretch", key="g_hall"
    )

# 7. Chart Hall Sensor Voltage
with st.container(border=True):
    st.markdown("#### Chart Hall Sensor Voltage")
    if len(df_chart) < 2:
        st.info(
            "⏳ Menunggu minimal 2 data dari Wokwi untuk menggambar grafik garis..."
        )
    else:
        st.line_chart(df_chart["hall_voltage"], color="#8b8c7a", width="stretch")

# 8. Magnetic Field Strength
with st.container(border=True):
    st.markdown("#### Magnetic Field Strength")
    st.plotly_chart(
        create_gauge(data["magnet_strength"], -2, 2), width="stretch", key="g_mag"
    )

# 9. Chart Magnetic Strength History
with st.container(border=True):
    st.markdown("#### Magnetic Strength History")
    if len(df_chart) < 2:
        st.info(
            "⏳ Menunggu minimal 2 data dari Wokwi untuk menggambar grafik garis..."
        )
    else:
        st.line_chart(df_chart["magnet_strength"], color="#6f697a", width="stretch")

# 10. Magnetic Pole Direction
with st.container(border=True):
    st.markdown("#### Magnetic Pole Direction")
    # Warna teks dihapus agar otomatis terang di Dark Mode
    st.markdown(
        f"<h1 style='font-weight:normal;'>{data['magnet_direction']}</h1>",
        unsafe_allow_html=True,
    )

# Refresh otomatis
time.sleep(1)
st.rerun()
