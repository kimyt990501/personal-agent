import aiohttp

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# 한글 도시명 → 영문 매핑 (Open-Meteo Geocoding이 한글 검색을 지원하지 않음)
CITY_MAP = {
    "서울": "Seoul",
    "부산": "Busan",
    "인천": "Incheon",
    "대구": "Daegu",
    "대전": "Daejeon",
    "광주": "Gwangju",
    "울산": "Ulsan",
    "세종": "Sejong",
    "수원": "Suwon",
    "성남": "Seongnam",
    "고양": "Goyang",
    "용인": "Yongin",
    "창원": "Changwon",
    "청주": "Cheongju",
    "전주": "Jeonju",
    "천안": "Cheonan",
    "제주": "Jeju",
    "포항": "Pohang",
    "김해": "Gimhae",
    "춘천": "Chuncheon",
    "여수": "Yeosu",
    "경주": "Gyeongju",
    "목포": "Mokpo",
    "강릉": "Gangneung",
    "속초": "Sokcho",
}

# WMO Weather Code → 한글 설명
WMO_CODES = {
    0: "맑음 ☀️",
    1: "대체로 맑음 🌤️",
    2: "구름 조금 ⛅",
    3: "흐림 ☁️",
    45: "안개 🌫️",
    48: "안개 🌫️",
    51: "약한 이슬비 🌦️",
    53: "이슬비 🌦️",
    55: "강한 이슬비 🌧️",
    61: "약한 비 🌦️",
    63: "비 🌧️",
    65: "강한 비 🌧️",
    66: "약한 빗방울 (어는 비) 🌧️",
    67: "강한 빗방울 (어는 비) 🌧️",
    71: "약한 눈 🌨️",
    73: "눈 ❄️",
    75: "강한 눈 ❄️",
    77: "싸라기눈 ❄️",
    80: "약한 소나기 🌦️",
    81: "소나기 🌧️",
    82: "강한 소나기 🌧️",
    85: "약한 눈보라 🌨️",
    86: "강한 눈보라 ❄️",
    95: "천둥번개 ⛈️",
    96: "우박 동반 천둥번개 ⛈️",
    99: "강한 우박 동반 천둥번개 ⛈️",
}


async def get_coordinates(city: str) -> tuple[float, float, str] | None:
    """Get coordinates for a city using Open-Meteo Geocoding API."""
    # 한글 도시명을 영문으로 변환
    display_name = city
    city_query = CITY_MAP.get(city, city)

    params = {
        "name": city_query,
        "count": 1,
        "language": "ko",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(GEOCODING_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get("results")
                    if results:
                        r = results[0]
                        name = r.get("name", display_name)
                        return (r["latitude"], r["longitude"], name)
    except Exception:
        pass
    return None


async def get_weather(city: str) -> dict | None:
    """Get current weather + today's forecast using Open-Meteo API."""
    coords = await get_coordinates(city)
    if not coords:
        return {"error": "city_not_found"}

    lat, lon, city_name = coords

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,uv_index_max,precipitation_probability_max",
        "timezone": "auto",
        "forecast_days": 1,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(FORECAST_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return _parse_weather(data, city_name)
    except Exception:
        pass
    return None


def _parse_weather(data: dict, city_name: str) -> dict:
    """Parse Open-Meteo API response."""
    current = data["current"]
    daily = data.get("daily", {})

    code = current.get("weather_code", 0)
    description = WMO_CODES.get(code, f"알 수 없음 ({code})")

    return {
        "city": city_name,
        "description": description,
        "temp": round(current["temperature_2m"], 1),
        "feels_like": round(current["apparent_temperature"], 1),
        "temp_min": round(daily["temperature_2m_min"][0], 1) if daily.get("temperature_2m_min") else None,
        "temp_max": round(daily["temperature_2m_max"][0], 1) if daily.get("temperature_2m_max") else None,
        "humidity": current["relative_humidity_2m"],
        "wind_speed": current["wind_speed_10m"],
        "uvi": round(daily["uv_index_max"][0], 1) if daily.get("uv_index_max") else 0,
        "rain_chance": daily["precipitation_probability_max"][0] if daily.get("precipitation_probability_max") else None,
    }


def format_weather(weather: dict) -> str:
    """Format weather data for display."""
    if "error" in weather:
        if weather["error"] == "city_not_found":
            return "해당 도시를 찾을 수 없어요. 다른 도시명으로 시도해주세요."
        return "날씨 정보를 가져오지 못했어요."

    uvi_desc = _get_uvi_level(weather['uvi'])

    lines = [
        f"**🌡️ {weather['city']} 날씨**\n",
        f"**상태:** {weather['description']}",
        f"**기온:** {weather['temp']}°C (체감 {weather['feels_like']}°C)",
    ]

    if weather.get("temp_min") is not None and weather.get("temp_max") is not None:
        lines.append(f"**최저/최고:** {weather['temp_min']}°C / {weather['temp_max']}°C")

    lines.append(f"**습도:** {weather['humidity']}%")
    lines.append(f"**풍속:** {weather['wind_speed']} m/s")
    lines.append(f"**자외선:** {weather['uvi']} ({uvi_desc})")

    if weather.get("rain_chance") is not None:
        lines.append(f"**강수 확률:** {weather['rain_chance']}%")

    return "\n".join(lines)


def _get_uvi_level(uvi: float) -> str:
    """Get UV index level description."""
    if uvi <= 2:
        return "낮음"
    elif uvi <= 5:
        return "보통"
    elif uvi <= 7:
        return "높음"
    elif uvi <= 10:
        return "매우 높음"
    else:
        return "위험"
