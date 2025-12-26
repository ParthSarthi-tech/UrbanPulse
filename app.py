import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
from utils.api import get_city_weather, get_city_aqi

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="UrbanPulse • Live City Intelligence",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -----------------------------
# ENHANCED GLOBAL STYLES
# -----------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

* {
    font-family: 'Inter', sans-serif;
}

body {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
}

.hero {
    animation: fadeSlide 0.8s ease forwards;
    background: linear-gradient(135deg, rgba(99,102,241,0.1) 0%, rgba(139,92,246,0.1) 100%);
    padding: 40px;
    border-radius: 24px;
    border: 1px solid rgba(139,92,246,0.3);
    backdrop-filter: blur(10px);
}

@keyframes fadeSlide {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

.metric-card {
    background: linear-gradient(135deg, rgba(30,41,59,0.8) 0%, rgba(15,23,42,0.9) 100%);
    padding: 28px;
    border-radius: 20px;
    text-align: center;
    border: 1px solid rgba(139,92,246,0.2);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    backdrop-filter: blur(10px);
    position: relative;
    overflow: hidden;
}

.metric-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(139,92,246,0.1), transparent);
    transition: left 0.5s;
}

.metric-card:hover::before {
    left: 100%;
}

.metric-card:hover {
    transform: translateY(-8px) scale(1.03);
    box-shadow: 0 20px 60px rgba(139,92,246,0.4);
    border-color: rgba(139,92,246,0.5);
}

.pulse {
    animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
}

.gradient-text {
    background: linear-gradient(135deg, #a78bfa 0%, #ec4899 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.comparison-card {
    background: rgba(30,41,59,0.6);
    padding: 20px;
    border-radius: 16px;
    border: 1px solid rgba(139,92,246,0.2);
    margin: 10px 0;
}

.alert-banner {
    background: linear-gradient(135deg, rgba(239,68,68,0.2) 0%, rgba(220,38,38,0.2) 100%);
    padding: 16px 24px;
    border-radius: 16px;
    border-left: 4px solid #ef4444;
    margin: 20px 0;
    animation: slideIn 0.5s ease;
}

@keyframes slideIn {
    from { transform: translateX(-20px); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}

.comfort-score {
    font-size: 72px;
    font-weight: 900;
    background: linear-gradient(135deg, #10b981 0%, #3b82f6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

[data-testid="stToolbar"],
footer {
    visibility: hidden;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}

.stTabs [data-baseweb="tab"] {
    background-color: rgba(30,41,59,0.5);
    border-radius: 12px;
    padding: 12px 24px;
    border: 1px solid rgba(139,92,246,0.2);
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(139,92,246,0.3) 0%, rgba(99,102,241,0.3) 100%);
    border-color: rgba(139,92,246,0.5);
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def metric_card(icon, label, value, subtitle=""):
    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size:32px; margin-bottom:8px;">{icon}</div>
        <div style="font-size:13px; color:#94a3b8; text-transform:uppercase; letter-spacing:1px; font-weight:600;">{label}</div>
        <div style="font-size:36px; font-weight:800; margin:8px 0;">{value}</div>
        {f'<div style="font-size:12px; color:#64748b;">{subtitle}</div>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)

def aqi_label_color(aqi):
    if aqi <= 50:
        return "Good", "#10b981", "😊"
    elif aqi <= 100:
        return "Moderate", "#facc15", "😐"
    elif aqi <= 200:
        return "Poor", "#fb923c", "😷"
    else:
        return "Very Poor", "#ef4444", "🚨"

def calculate_comfort_score(temp, humidity, aqi):
    """Calculate a comfort score (0-100) based on weather conditions"""
    temp_score = max(0, 100 - abs(temp - 25) * 3)
    humidity_score = max(0, 100 - abs(humidity - 50) * 1.5)
    aqi_score = max(0, 100 - aqi * 0.8)
    return round((temp_score + humidity_score + aqi_score) / 3, 1)

def get_comfort_emoji(score):
    if score >= 80: return "🌟"
    elif score >= 60: return "👍"
    elif score >= 40: return "😐"
    else: return "😰"

def feels_like_temp(temp, humidity, wind):
    """Calculate feels-like temperature"""
    heat_index = temp + (0.5555 * (6.11 * np.exp(5417.7530 * ((1/273.16) - (1/(273.15+temp)))) * (humidity/100) - 10))
    wind_chill = 13.12 + 0.6215*temp - 11.37*(wind**0.16) + 0.3965*temp*(wind**0.16)
    if temp > 27:
        return round(heat_index, 1)
    elif temp < 10:
        return round(wind_chill, 1)
    else:
        return round(temp, 1)

# -----------------------------
# APP HEADER
# -----------------------------
st.markdown("""
<div class="hero">
    <h1 style="font-size:56px; margin-bottom:8px; font-weight:900;">
        🏙️ <span class="gradient-text">UrbanPulse</span>
    </h1>
    <p style="color:#cbd5e1; font-size:20px; margin:0;">
        Real-Time City Intelligence • Environment Analytics • Comfort Insights
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------
# CITY SELECTION & COMPARISON
# -----------------------------
col1, col2 = st.columns([2, 1])

with col1:
    CITIES = ["Delhi", "Mumbai", "Bangalore", "Pune", "Hyderabad", "Bhopal", "Chennai", "Kolkata"]
    city = st.selectbox("🎯 Select Primary City", CITIES, key="primary_city")

with col2:
    compare_city = st.selectbox("📊 Compare With", ["None"] + [c for c in CITIES if c != city], key="compare_city")

# -----------------------------
# FETCH LIVE DATA
# -----------------------------
with st.spinner("🔄 Fetching live city data..."):
    weather = get_city_weather(city)
    lat = weather["coord"]["lat"]
    lon = weather["coord"]["lon"]
    aqi_data = get_city_aqi(lat, lon)
    
    if compare_city != "None":
        weather_compare = get_city_weather(compare_city)
        lat_c = weather_compare["coord"]["lat"]
        lon_c = weather_compare["coord"]["lon"]
        aqi_data_compare = get_city_aqi(lat_c, lon_c)

# -----------------------------
# EXTRACT METRICS
# -----------------------------
temp = weather["main"]["temp"]
humidity = weather["main"]["humidity"]
wind = weather["wind"]["speed"]
pressure = weather["main"]["pressure"]
visibility = weather.get("visibility", 10000) / 1000
condition = weather["weather"][0]["description"].title()
icon_code = weather["weather"][0]["icon"]

aqi = aqi_data["aqi"]
pm25 = aqi_data["pm25"]
co = aqi_data["co"]
no2 = aqi_data["no2"]
o3 = aqi_data["o3"]


aqi_text, aqi_color, aqi_emoji = aqi_label_color(aqi)
feels_like = feels_like_temp(temp, humidity, wind)
comfort_score = calculate_comfort_score(temp, humidity, aqi)
comfort_emoji = get_comfort_emoji(comfort_score)

updated_time = datetime.now().strftime("%H:%M IST")
sunrise = datetime.fromtimestamp(weather["sys"]["sunrise"]).strftime("%H:%M")
sunset = datetime.fromtimestamp(weather["sys"]["sunset"]).strftime("%H:%M")

# -----------------------------
# HERO CARD WITH ENHANCED INFO
# -----------------------------
st.markdown(f"""
<div style="
    background: linear-gradient(135deg, rgba(30,41,59,0.8) 0%, rgba(15,23,42,0.9) 100%);
    padding: 40px;
    border-radius: 24px;
    margin-top: 24px;
    border: 1px solid rgba(139,92,246,0.3);
    backdrop-filter: blur(10px);
">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
        <div>
            <h2 style="margin:0; font-size:32px;">📍 {city}, India</h2>
            <p style="font-size:80px; font-weight:900; margin:16px 0 8px 0; line-height:1;">
                {temp:.1f}°C
            </p>
            <p style="color:#94a3b8; font-size:20px; margin:8px 0;">
                {condition} • Feels like {feels_like}°C
            </p>
            <p style="color:#64748b; font-size:16px;">
                🌅 {sunrise} • 🌇 {sunset} • Updated {updated_time}
            </p>
        </div>
        <div style="text-align:center;">
            <div class="comfort-score pulse">{comfort_emoji}</div>
            <div style="font-size:48px; font-weight:900; color:#a78bfa;">{comfort_score}</div>
            <div style="color:#94a3b8; font-size:14px; text-transform:uppercase;">Comfort Score</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# -----------------------------
# AIR QUALITY ALERT
# -----------------------------
if aqi > 100:
    st.markdown(f"""
    <div class="alert-banner">
        <strong>⚠️ Air Quality Alert</strong><br>
        Current AQI is {aqi:.1f} ({aqi_text}). Consider limiting outdoor activities and wearing a mask.
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------
# METRIC CARDS
# -----------------------------
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    metric_card("🌡️", "Temperature", f"{temp:.1f}°C", f"Feels {feels_like}°C")

with c2:
    metric_card("💧", "Humidity", f"{humidity}%", "Moisture Level")

with c3:
    metric_card("🌬️", "Wind Speed", f"{wind:.1f} m/s", f"{wind*3.6:.1f} km/h")

with c4:
    metric_card("🔍", "Visibility", f"{visibility:.1f} km", "Clear View")

with c5:
    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size:32px; margin-bottom:8px;">{aqi_emoji}</div>
        <div style="font-size:13px; color:#94a3b8; text-transform:uppercase; letter-spacing:1px; font-weight:600;">AQI (PM2.5)</div>
        <div style="font-size:36px; font-weight:800; margin:8px 0;">{aqi:.1f}</div>
        <span style="
            padding:8px 16px;
            border-radius:999px;
            background:{aqi_color};
            color:#000;
            font-weight:700;
            font-size:13px;
            display:inline-block;
        ">
            {aqi_text}
        </span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)

# -----------------------------
# TABS FOR DIFFERENT VIEWS
# -----------------------------
tab1, tab2, tab3, tab4 = st.tabs(["📈 Trends & Forecast", "🫁 Air Quality Deep Dive", "⚖️ City Comparison", "🎯 Recommendations"])

with tab1:
    st.markdown("### 7-Day Temperature Forecast")
    
    # Simulated forecast data
    dates = [(datetime.now() + timedelta(days=i)).strftime("%a %d") for i in range(7)]
    temps_high = [temp + np.random.randint(-3, 5) for _ in range(7)]
    temps_low = [t - np.random.randint(3, 8) for t in temps_high]
    
    forecast_df = pd.DataFrame({
        "Date": dates,
        "High": temps_high,
        "Low": temps_low
    })
    
    fig_forecast = go.Figure()
    
    fig_forecast.add_trace(go.Scatter(
        x=forecast_df["Date"],
        y=forecast_df["High"],
        mode='lines+markers',
        name='High',
        line=dict(color='#ef4444', width=3),
        marker=dict(size=10)
    ))
    
    fig_forecast.add_trace(go.Scatter(
        x=forecast_df["Date"],
        y=forecast_df["Low"],
        mode='lines+markers',
        name='Low',
        line=dict(color='#3b82f6', width=3),
        marker=dict(size=10),
        fill='tonexty',
        fillcolor='rgba(139,92,246,0.1)'
    ))
    
    fig_forecast.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white", size=14),
        height=400,
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig_forecast, use_container_width=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Hourly Temperature Pattern")
        hours = [f"{i:02d}:00" for i in range(0, 24, 3)]
        temps_hourly = [temp + np.sin(i/24 * 2 * np.pi) * 5 for i in range(0, 24, 3)]
        
        fig_hourly = px.bar(
            x=hours,
            y=temps_hourly,
            labels={'x': 'Hour', 'y': 'Temperature (°C)'},
            color=temps_hourly,
            color_continuous_scale='RdYlBu_r'
        )
        
        fig_hourly.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            showlegend=False,
            height=300
        )
        
        st.plotly_chart(fig_hourly, use_container_width=True)
    
    with col2:
        st.markdown("### Weather Comfort Index")
        comfort_factors = ['Temperature', 'Humidity', 'Air Quality', 'Wind', 'Visibility']
        comfort_scores = [
            max(0, 100 - abs(temp - 25) * 3),
            max(0, 100 - abs(humidity - 50) * 1.5),
            max(0, 100 - aqi * 0.8),
            min(100, wind * 20),
            min(100, visibility * 10)
        ]
        
        fig_radar = go.Figure(data=go.Scatterpolar(
            r=comfort_scores,
            theta=comfort_factors,
            fill='toself',
            fillcolor='rgba(139,92,246,0.3)',
            line=dict(color='#a78bfa', width=2)
        ))
        
        fig_radar.update_layout(
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(visible=True, range=[0, 100], gridcolor='rgba(255,255,255,0.1)')
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            height=300
        )
        
        st.plotly_chart(fig_radar, use_container_width=True)

with tab2:
    st.markdown("### Air Quality Composition")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        pollutants = ['PM2.5', 'CO', 'NO₂', 'O₃']
        values = [aqi, co/100, no2, o3]
        colors = ['#ef4444', '#f59e0b', '#8b5cf6', '#06b6d4']
        
        fig_pollutants = go.Figure(data=[go.Bar(
            x=pollutants,
            y=values,
            marker=dict(
                color=colors,
                line=dict(color='rgba(255,255,255,0.2)', width=2)
            ),
            text=[f'{v:.1f}' for v in values],
            textposition='auto',
        )])
        
        fig_pollutants.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white", size=14),
            height=350,
            yaxis=dict(title="Concentration (μg/m³)"),
            showlegend=False
        )
        
        st.plotly_chart(fig_pollutants, use_container_width=True)
    
    with col2:
        st.markdown("### Health Impact")
        st.markdown(f"""
        <div style="background:rgba(30,41,59,0.6); padding:20px; border-radius:16px; margin-top:30px;">
            <h4 style="margin-top:0;">Current Level: {aqi_text}</h4>
            <p style="color:#94a3b8; font-size:14px; line-height:1.6;">
                {"✅ Safe for all outdoor activities" if aqi <= 50 else 
                 "⚠️ Sensitive groups should limit prolonged outdoor exertion" if aqi <= 100 else
                 "🚨 Everyone should reduce outdoor exertion" if aqi <= 200 else
                 "❌ Avoid all outdoor activities"}
            </p>
            <br>
            <div style="font-size:12px; color:#64748b;">
                <strong>PM2.5:</strong> {aqi:.1f} μg/m³<br>
                <strong>CO:</strong> {co:.1f} μg/m³<br>
                <strong>NO₂:</strong> {no2:.1f} μg/m³<br>
                <strong>O₃:</strong> {o3:.1f} μg/m³
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("### AQI Trend (Simulated 24h)")
    
    hours_aqi = list(range(24))
    aqi_trend = [aqi + np.random.randint(-15, 20) for _ in hours_aqi]
    
    fig_aqi_trend = px.area(
        x=hours_aqi,
        y=aqi_trend,
        labels={'x': 'Hour', 'y': 'PM2.5 (μg/m³)'}
    )
    
    fig_aqi_trend.add_hline(y=50, line_dash="dash", line_color="#10b981", annotation_text="Good")
    fig_aqi_trend.add_hline(y=100, line_dash="dash", line_color="#facc15", annotation_text="Moderate")
    
    fig_aqi_trend.update_traces(fillcolor='rgba(139,92,246,0.3)', line=dict(color='#a78bfa', width=3))
    
    fig_aqi_trend.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        height=300
    )
    
    st.plotly_chart(fig_aqi_trend, use_container_width=True)

with tab3:
    if compare_city != "None":
        st.markdown(f"### {city} vs {compare_city}")
        
        temp_c = weather_compare["main"]["temp"]
        humidity_c = weather_compare["main"]["humidity"]
        wind_c = weather_compare["wind"]["speed"]
        aqi_c = aqi_data_compare["aqi"]
        comfort_c = calculate_comfort_score(temp_c, humidity_c, aqi_c)
        
        comparison_data = {
            'Metric': ['Temperature (°C)', 'Humidity (%)', 'Wind Speed (m/s)', 'AQI (PM2.5)', 'Comfort Score'],
            city: [temp, humidity, wind, aqi, comfort_score],
            compare_city: [temp_c, humidity_c, wind_c, aqi_c, comfort_c]
        }
        
        df_comparison = pd.DataFrame(comparison_data)
        
        fig_comparison = go.Figure(data=[
            go.Bar(name=city, x=df_comparison['Metric'], y=df_comparison[city], marker_color='#a78bfa'),
            go.Bar(name=compare_city, x=df_comparison['Metric'], y=df_comparison[compare_city], marker_color='#ec4899')
        ])
        
        fig_comparison.update_layout(
            barmode='group',
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white", size=14),
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig_comparison, use_container_width=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            <div class="comparison-card">
                <h3>🏙️ {city}</h3>
                <div style="font-size:42px; font-weight:900; color:#a78bfa;">{comfort_score}</div>
                <div style="color:#94a3b8;">Comfort Score</div>
                <br>
                <div style="font-size:14px; color:#cbd5e1;">
                    🌡️ {temp:.1f}°C • 💧 {humidity}%<br>
                    🌬️ {wind:.1f} m/s • {aqi_emoji} AQI {aqi:.1f}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="comparison-card">
                <h3>🏙️ {compare_city}</h3>
                <div style="font-size:42px; font-weight:900; color:#ec4899;">{comfort_c}</div>
                <div style="color:#94a3b8;">Comfort Score</div>
                <br>
                <div style="font-size:14px; color:#cbd5e1;">
                    🌡️ {temp_c:.1f}°C • 💧 {humidity_c}%<br>
                    🌬️ {wind_c:.1f} m/s • {aqi_label_color(aqi_c)[2]} AQI {aqi_c:.1f}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        winner = city if comfort_score > comfort_c else compare_city
        st.markdown(f"""
        <div style="text-align:center; margin-top:30px; font-size:24px; color:#a78bfa;">
            🏆 <strong>{winner}</strong> has better weather conditions today!
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("👆 Select a city to compare from the dropdown above")

with tab4:
    st.markdown("### Personalized Recommendations")
    
    recommendations = []
    
    if temp > 35:
        recommendations.append(("🌡️ High Temperature Alert", "Stay hydrated and avoid direct sun exposure between 11 AM - 4 PM", "#ef4444"))
    elif temp < 15:
        recommendations.append(("🧥 Cold Weather", "Wear warm clothing and stay protected from wind chill", "#3b82f6"))
    
    if aqi > 100:
        recommendations.append(("😷 Poor Air Quality", "Wear an N95 mask outdoors and use air purifiers indoors", "#fb923c"))
    
    if humidity > 70:
        recommendations.append(("💧 High Humidity", "Use dehumidifiers indoors and stay in air-conditioned spaces", "#06b6d4"))
    
    if wind > 10:
        recommendations.append(("🌪️ Windy Conditions", "Secure loose objects and avoid high-rise areas", "#8b5cf6"))
    
    if comfort_score > 80:
        recommendations.append(("✨ Perfect Weather", "Great day for outdoor activities and exercise!", "#10b981"))
    
    if not recommendations:
        recommendations.append(("👍 Normal Conditions", "Weather conditions are moderate. Enjoy your day!", "#10b981"))
    
    for title, desc, color in recommendations:
        st.markdown(f"""
        <div style="
            background:rgba(30,41,59,0.6);
            padding:20px;
            border-radius:16px;
            margin:12px 0;
            border-left:4px solid {color};
        ">
            <strong style="font-size:18px;">{title}</strong><br>
            <span style="color:#94a3b8; font-size:15px;">{desc}</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("### Best Time to Go Outside Today")
    
    hours_comfort = list(range(24))
    comfort_by_hour = [comfort_score + np.sin((h-12)/24 * 2 * np.pi) * 15 for h in hours_comfort]
    
    fig_best_time = px.line(
        x=hours_comfort,
        y=comfort_by_hour,
        labels={'x': 'Hour of Day', 'y': 'Comfort Score'}
    )
    
    fig_best_time.add_hline(y=70, line_dash="dash", line_color="#10b981", annotation_text="Good")
    
    fig_best_time.update_traces(line=dict(color='#a78bfa', width=3), fill='tozeroy', fillcolor='rgba(139,92,246,0.2)')
    
    fig_best_time.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        height=300
    )
    
    st.plotly_chart(fig_best_time, use_container_width=True)
    
    best_hour = hours_comfort[comfort_by_hour.index(max(comfort_by_hour))]
    st.markdown(f"""
    <div style="text-align:center; font-size:20px; color:#a78bfa; margin-top:20px;">
        ⏰ Best time to go outside: <strong>{best_hour:02d}:00 - {(best_hour+2)%24:02d}:00</strong>
    </div>
    """, unsafe_allow_html=True)