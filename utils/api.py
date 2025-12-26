import os
import requests

BASE_WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
BASE_AIR_URL = "https://api.openweathermap.org/data/2.5/air_pollution"


def get_api_key():
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENWEATHER_API_KEY not set")
    return api_key


def get_city_weather(city):
    api_key = get_api_key()
    params = {"q": city, "appid": api_key, "units": "metric"}
    res = requests.get(BASE_WEATHER_URL, params=params)
    res.raise_for_status()
    return res.json()


# -------------------------------
# PM2.5 → AQI (US EPA STANDARD)
# -------------------------------
def pm25_to_aqi(pm25):
    breakpoints = [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 350.4, 301, 400),
        (350.5, 500.4, 401, 500),
    ]

    for c_low, c_high, aqi_low, aqi_high in breakpoints:
        if c_low <= pm25 <= c_high:
            return round(
                ((aqi_high - aqi_low) / (c_high - c_low)) * (pm25 - c_low) + aqi_low
            )

    return 500


def get_city_aqi(lat, lon):
    api_key = get_api_key()
    params = {"lat": lat, "lon": lon, "appid": api_key}
    res = requests.get(BASE_AIR_URL, params=params)
    res.raise_for_status()

    data = res.json()
    components = data["list"][0]["components"]

    pm25 = components["pm2_5"]
    aqi = pm25_to_aqi(pm25)

    return {
        "aqi": aqi,
        "pm25": pm25,
        "co": components["co"],
        "no2": components["no2"],
        "o3": components["o3"]
    }
