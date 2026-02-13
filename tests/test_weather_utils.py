"""Tests for src/utils/weather.py - pure function tests"""
import pytest

from src.utils.weather import _parse_weather, format_weather, _get_uvi_level, CITY_MAP, WMO_CODES


# ─── _get_uvi_level ───

class TestGetUviLevel:
    def test_low(self):
        assert _get_uvi_level(0) == "낮음"
        assert _get_uvi_level(2) == "낮음"

    def test_moderate(self):
        assert _get_uvi_level(3) == "보통"
        assert _get_uvi_level(5) == "보통"

    def test_high(self):
        assert _get_uvi_level(6) == "높음"
        assert _get_uvi_level(7) == "높음"

    def test_very_high(self):
        assert _get_uvi_level(8) == "매우 높음"
        assert _get_uvi_level(10) == "매우 높음"

    def test_extreme(self):
        assert _get_uvi_level(11) == "위험"
        assert _get_uvi_level(15) == "위험"

    def test_negative_is_low(self):
        """음수 UVI도 '낮음'으로 처리되어야 함"""
        assert _get_uvi_level(-1) == "낮음"


# ─── _parse_weather ───

class TestParseWeather:
    def _make_api_response(self, **overrides):
        """Open-Meteo API 응답 형태의 테스트 데이터 생성"""
        data = {
            "current": {
                "temperature_2m": 3.2,
                "apparent_temperature": -1.0,
                "relative_humidity_2m": 45,
                "wind_speed_10m": 5.3,
                "weather_code": 0,
            },
            "daily": {
                "temperature_2m_min": [0.5],
                "temperature_2m_max": [7.8],
                "uv_index_max": [3.5],
                "precipitation_probability_max": [10],
            },
        }
        data.update(overrides)
        return data

    def test_basic_parsing(self):
        data = self._make_api_response()
        result = _parse_weather(data, "서울")

        assert result["city"] == "서울"
        assert result["temp"] == 3.2
        assert result["feels_like"] == -1.0
        assert result["humidity"] == 45
        assert result["wind_speed"] == 5.3
        assert result["description"] == "맑음 ☀️"
        assert result["temp_min"] == 0.5
        assert result["temp_max"] == 7.8
        assert result["uvi"] == 3.5
        assert result["rain_chance"] == 10

    def test_unknown_weather_code(self):
        data = self._make_api_response()
        data["current"]["weather_code"] = 999
        result = _parse_weather(data, "서울")
        assert "알 수 없음" in result["description"]

    def test_missing_daily_data(self):
        """daily 데이터가 없는 경우"""
        data = self._make_api_response()
        data["daily"] = {}
        result = _parse_weather(data, "서울")
        assert result["temp_min"] is None
        assert result["temp_max"] is None
        assert result["uvi"] == 0
        assert result["rain_chance"] is None


# ─── format_weather ───

class TestFormatWeather:
    def test_normal_weather(self):
        weather = {
            "city": "서울",
            "description": "맑음 ☀️",
            "temp": 3.2,
            "feels_like": -1.0,
            "temp_min": 0.5,
            "temp_max": 7.8,
            "humidity": 45,
            "wind_speed": 5.3,
            "uvi": 3.5,
            "rain_chance": 10,
        }
        result = format_weather(weather)
        assert "서울" in result
        assert "3.2°C" in result
        assert "-1.0°C" in result
        assert "0.5°C" in result
        assert "7.8°C" in result
        assert "45%" in result
        assert "5.3 m/s" in result
        assert "10%" in result

    def test_error_city_not_found(self):
        result = format_weather({"error": "city_not_found"})
        assert "찾을 수 없" in result

    def test_error_generic(self):
        result = format_weather({"error": "api_error"})
        assert "가져오지 못했" in result

    def test_no_temp_min_max(self):
        weather = {
            "city": "서울",
            "description": "맑음 ☀️",
            "temp": 3.2,
            "feels_like": -1.0,
            "temp_min": None,
            "temp_max": None,
            "humidity": 45,
            "wind_speed": 5.3,
            "uvi": 3.5,
            "rain_chance": None,
        }
        result = format_weather(weather)
        assert "최저/최고" not in result
        assert "강수 확률" not in result

    def test_no_rain_chance(self):
        weather = {
            "city": "제주",
            "description": "흐림 ☁️",
            "temp": 10.0,
            "feels_like": 8.0,
            "temp_min": 7.0,
            "temp_max": 13.0,
            "humidity": 70,
            "wind_speed": 3.0,
            "uvi": 1.0,
            "rain_chance": None,
        }
        result = format_weather(weather)
        assert "강수 확률" not in result


# ─── CITY_MAP ───

class TestCityMap:
    def test_major_cities_exist(self):
        assert "서울" in CITY_MAP
        assert "부산" in CITY_MAP
        assert "제주" in CITY_MAP
        assert "인천" in CITY_MAP

    def test_english_mapping(self):
        assert CITY_MAP["서울"] == "Seoul"
        assert CITY_MAP["부산"] == "Busan"
        assert CITY_MAP["제주"] == "Jeju"


# ─── WMO_CODES ───

class TestWmoCodes:
    def test_clear_sky(self):
        assert WMO_CODES[0] == "맑음 ☀️"

    def test_rain_codes_exist(self):
        assert 61 in WMO_CODES  # 약한 비
        assert 63 in WMO_CODES  # 비
        assert 65 in WMO_CODES  # 강한 비

    def test_snow_codes_exist(self):
        assert 71 in WMO_CODES  # 약한 눈
        assert 73 in WMO_CODES  # 눈
        assert 75 in WMO_CODES  # 강한 눈
