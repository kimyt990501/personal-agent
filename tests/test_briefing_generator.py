"""Tests for generate_briefing() - daily briefing content generation."""

from unittest.mock import AsyncMock, patch
from datetime import date

import pytest

from src.utils.briefing_generator import generate_briefing


USER_ID = "test_user_123"


@pytest.fixture
def mock_reminder_db():
    db = AsyncMock()
    db.get_all = AsyncMock(return_value=[])
    return db


class TestGenerateBriefingWeather:
    @pytest.mark.asyncio
    @patch("src.utils.briefing_generator.web_search", new_callable=AsyncMock)
    @patch("src.utils.briefing_generator.get_weather", new_callable=AsyncMock)
    async def test_weather_section_included(self, mock_weather, mock_search, mock_reminder_db):
        mock_weather.return_value = {
            "city": "서울",
            "description": "맑음",
            "temp": 15,
            "feels_like": 13,
            "temp_min": 10,
            "temp_max": 20,
            "humidity": 45,
        }
        mock_search.return_value = []

        result = await generate_briefing("서울", USER_ID, mock_reminder_db)

        assert "날씨" in result
        assert "서울" in result
        assert "15°C" in result
        assert "맑음" in result

    @pytest.mark.asyncio
    @patch("src.utils.briefing_generator.web_search", new_callable=AsyncMock)
    @patch("src.utils.briefing_generator.get_weather", new_callable=AsyncMock)
    async def test_weather_with_rain_chance(self, mock_weather, mock_search, mock_reminder_db):
        mock_weather.return_value = {
            "city": "서울",
            "description": "흐림",
            "temp": 10,
            "feels_like": 8,
            "temp_min": 5,
            "temp_max": 12,
            "humidity": 80,
            "rain_chance": 70,
        }
        mock_search.return_value = []

        result = await generate_briefing("서울", USER_ID, mock_reminder_db)
        assert "70%" in result
        assert "강수확률" in result

    @pytest.mark.asyncio
    @patch("src.utils.briefing_generator.web_search", new_callable=AsyncMock)
    @patch("src.utils.briefing_generator.get_weather", new_callable=AsyncMock)
    async def test_weather_error_handled(self, mock_weather, mock_search, mock_reminder_db):
        mock_weather.return_value = {"error": "API 오류"}
        mock_search.return_value = []

        result = await generate_briefing("서울", USER_ID, mock_reminder_db)
        assert "가져올 수 없습니다" in result

    @pytest.mark.asyncio
    @patch("src.utils.briefing_generator.web_search", new_callable=AsyncMock)
    @patch("src.utils.briefing_generator.get_weather", new_callable=AsyncMock)
    async def test_weather_exception_handled(self, mock_weather, mock_search, mock_reminder_db):
        mock_weather.side_effect = Exception("Network error")
        mock_search.return_value = []

        result = await generate_briefing("서울", USER_ID, mock_reminder_db)
        assert "가져올 수 없습니다" in result


class TestGenerateBriefingReminders:
    @pytest.mark.asyncio
    @patch("src.utils.briefing_generator.web_search", new_callable=AsyncMock)
    @patch("src.utils.briefing_generator.get_weather", new_callable=AsyncMock)
    async def test_today_reminders_shown(self, mock_weather, mock_search, mock_reminder_db):
        mock_weather.return_value = {"error": "skip"}
        mock_search.return_value = []

        today = date.today().strftime("%Y-%m-%d")
        mock_reminder_db.get_all.return_value = [
            {"remind_at": f"{today} 09:00:00", "content": "회의 참석"},
            {"remind_at": f"{today} 14:30:00", "content": "보고서 제출"},
        ]

        result = await generate_briefing("서울", USER_ID, mock_reminder_db)
        assert "리마인더" in result
        assert "회의 참석" in result
        assert "보고서 제출" in result
        assert "09:00" in result
        assert "14:30" in result

    @pytest.mark.asyncio
    @patch("src.utils.briefing_generator.web_search", new_callable=AsyncMock)
    @patch("src.utils.briefing_generator.get_weather", new_callable=AsyncMock)
    async def test_no_reminders_message(self, mock_weather, mock_search, mock_reminder_db):
        mock_weather.return_value = {"error": "skip"}
        mock_search.return_value = []
        mock_reminder_db.get_all.return_value = []

        result = await generate_briefing("서울", USER_ID, mock_reminder_db)
        assert "예정된 리마인더가 없습니다" in result

    @pytest.mark.asyncio
    @patch("src.utils.briefing_generator.web_search", new_callable=AsyncMock)
    @patch("src.utils.briefing_generator.get_weather", new_callable=AsyncMock)
    async def test_only_today_reminders_filtered(self, mock_weather, mock_search, mock_reminder_db):
        mock_weather.return_value = {"error": "skip"}
        mock_search.return_value = []

        today = date.today().strftime("%Y-%m-%d")
        mock_reminder_db.get_all.return_value = [
            {"remind_at": f"{today} 09:00:00", "content": "오늘 할 일"},
            {"remind_at": "2026-12-31 09:00:00", "content": "미래 일정"},
        ]

        result = await generate_briefing("서울", USER_ID, mock_reminder_db)
        assert "오늘 할 일" in result
        assert "미래 일정" not in result

    @pytest.mark.asyncio
    @patch("src.utils.briefing_generator.web_search", new_callable=AsyncMock)
    @patch("src.utils.briefing_generator.get_weather", new_callable=AsyncMock)
    async def test_reminder_exception_handled(self, mock_weather, mock_search, mock_reminder_db):
        mock_weather.return_value = {"error": "skip"}
        mock_search.return_value = []
        mock_reminder_db.get_all.side_effect = Exception("DB error")

        result = await generate_briefing("서울", USER_ID, mock_reminder_db)
        assert "가져올 수 없습니다" in result


class TestGenerateBriefingNews:
    @pytest.mark.asyncio
    @patch("src.utils.briefing_generator.format_search_results")
    @patch("src.utils.briefing_generator.web_search", new_callable=AsyncMock)
    @patch("src.utils.briefing_generator.get_weather", new_callable=AsyncMock)
    async def test_news_section_included(self, mock_weather, mock_search, mock_format, mock_reminder_db):
        mock_weather.return_value = {"error": "skip"}
        mock_search.return_value = [
            {"title": "뉴스1", "body": "내용1", "href": "https://example.com"},
        ]
        mock_format.return_value = "1. **뉴스1**\n   내용1\n   링크: https://example.com"

        result = await generate_briefing("서울", USER_ID, mock_reminder_db)
        assert "뉴스" in result
        assert "뉴스1" in result

    @pytest.mark.asyncio
    @patch("src.utils.briefing_generator.web_search", new_callable=AsyncMock)
    @patch("src.utils.briefing_generator.get_weather", new_callable=AsyncMock)
    async def test_news_empty_results(self, mock_weather, mock_search, mock_reminder_db):
        mock_weather.return_value = {"error": "skip"}
        mock_search.return_value = []

        result = await generate_briefing("서울", USER_ID, mock_reminder_db)
        assert "뉴스" in result
        assert "가져올 수 없습니다" in result

    @pytest.mark.asyncio
    @patch("src.utils.briefing_generator.web_search", new_callable=AsyncMock)
    @patch("src.utils.briefing_generator.get_weather", new_callable=AsyncMock)
    async def test_news_exception_handled(self, mock_weather, mock_search, mock_reminder_db):
        mock_weather.return_value = {"error": "skip"}
        mock_search.side_effect = Exception("Search API error")

        result = await generate_briefing("서울", USER_ID, mock_reminder_db)
        assert "가져올 수 없습니다" in result


class TestGenerateBriefingStructure:
    @pytest.mark.asyncio
    @patch("src.utils.briefing_generator.web_search", new_callable=AsyncMock)
    @patch("src.utils.briefing_generator.get_weather", new_callable=AsyncMock)
    async def test_has_header(self, mock_weather, mock_search, mock_reminder_db):
        mock_weather.return_value = {"error": "skip"}
        mock_search.return_value = []

        result = await generate_briefing("서울", USER_ID, mock_reminder_db)
        assert "일일 브리핑" in result

    @pytest.mark.asyncio
    @patch("src.utils.briefing_generator.web_search", new_callable=AsyncMock)
    @patch("src.utils.briefing_generator.get_weather", new_callable=AsyncMock)
    async def test_has_footer(self, mock_weather, mock_search, mock_reminder_db):
        mock_weather.return_value = {"error": "skip"}
        mock_search.return_value = []

        result = await generate_briefing("서울", USER_ID, mock_reminder_db)
        assert "좋은 하루" in result

    @pytest.mark.asyncio
    @patch("src.utils.briefing_generator.web_search", new_callable=AsyncMock)
    @patch("src.utils.briefing_generator.get_weather", new_callable=AsyncMock)
    async def test_returns_string(self, mock_weather, mock_search, mock_reminder_db):
        mock_weather.return_value = {"error": "skip"}
        mock_search.return_value = []

        result = await generate_briefing("서울", USER_ID, mock_reminder_db)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    @patch("src.utils.briefing_generator.web_search", new_callable=AsyncMock)
    @patch("src.utils.briefing_generator.get_weather", new_callable=AsyncMock)
    async def test_all_sections_present(self, mock_weather, mock_search, mock_reminder_db):
        """날씨, 리마인더, 뉴스 3개 섹션 모두 포함"""
        mock_weather.return_value = {"error": "skip"}
        mock_search.return_value = []

        result = await generate_briefing("서울", USER_ID, mock_reminder_db)
        assert "날씨" in result
        assert "리마인더" in result
        assert "뉴스" in result
