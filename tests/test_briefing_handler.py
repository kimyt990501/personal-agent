"""Tests for BriefingHandler command routing."""

from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
import pytest_asyncio

from src.bot.handlers.briefing import BriefingHandler


USER_ID = "test_user_123"


@pytest_asyncio.fixture
async def handler():
    mock_db = MagicMock()
    mock_db.briefing = AsyncMock()
    h = BriefingHandler(mock_db)
    return h


@pytest.fixture
def message():
    msg = AsyncMock()
    msg.reply = AsyncMock()
    return msg


class TestBriefingHandleOn:
    @pytest.mark.asyncio
    async def test_enable(self, handler, message):
        await handler.handle(message, USER_ID, "on")
        handler.db.briefing.set_settings.assert_called_once_with(USER_ID, enabled=True)
        message.reply.assert_called_once()
        assert "활성화" in message.reply.call_args[0][0]

    @pytest.mark.asyncio
    async def test_disable(self, handler, message):
        await handler.handle(message, USER_ID, "off")
        handler.db.briefing.set_settings.assert_called_once_with(USER_ID, enabled=False)
        message.reply.assert_called_once()
        assert "비활성화" in message.reply.call_args[0][0]


class TestBriefingHandleTime:
    @pytest.mark.asyncio
    async def test_set_valid_time(self, handler, message):
        await handler.handle(message, USER_ID, "time 07:00")
        handler.db.briefing.set_settings.assert_called_once_with(USER_ID, time="07:00")
        assert "07:00" in message.reply.call_args[0][0]

    @pytest.mark.asyncio
    async def test_set_invalid_time(self, handler, message):
        await handler.handle(message, USER_ID, "time 오전7시")
        handler.db.briefing.set_settings.assert_not_called()
        assert "형식이 올바르지" in message.reply.call_args[0][0]

    @pytest.mark.asyncio
    async def test_set_time_no_colon(self, handler, message):
        await handler.handle(message, USER_ID, "time 0700")
        handler.db.briefing.set_settings.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_time_out_of_range_hour(self, handler, message):
        """BUG-006 수정 확인: 25시 거부"""
        await handler.handle(message, USER_ID, "time 25:00")
        handler.db.briefing.set_settings.assert_not_called()
        assert "올바르지 않습니다" in message.reply.call_args[0][0]

    @pytest.mark.asyncio
    async def test_set_time_out_of_range_minute(self, handler, message):
        """BUG-006 수정 확인: 60분 거부"""
        await handler.handle(message, USER_ID, "time 12:60")
        handler.db.briefing.set_settings.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_time_non_numeric(self, handler, message):
        """BUG-006 수정 확인: 숫자가 아닌 값 거부"""
        await handler.handle(message, USER_ID, "time ab:cd")
        handler.db.briefing.set_settings.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_time_boundary_2359(self, handler, message):
        """23:59 — 유효 경계값"""
        await handler.handle(message, USER_ID, "time 23:59")
        handler.db.briefing.set_settings.assert_called_once_with(USER_ID, time="23:59")

    @pytest.mark.asyncio
    async def test_set_time_boundary_0000(self, handler, message):
        """00:00 — 유효 경계값"""
        await handler.handle(message, USER_ID, "time 00:00")
        handler.db.briefing.set_settings.assert_called_once_with(USER_ID, time="00:00")


class TestBriefingHandleCity:
    @pytest.mark.asyncio
    async def test_set_city(self, handler, message):
        await handler.handle(message, USER_ID, "city 부산")
        handler.db.briefing.set_settings.assert_called_once_with(USER_ID, city="부산")
        assert "부산" in message.reply.call_args[0][0]


class TestBriefingHandleShowSettings:
    @pytest.mark.asyncio
    async def test_show_default_settings(self, handler, message):
        """설정이 없을 때 기본값 표시"""
        handler.db.briefing.get_settings = AsyncMock(return_value=None)
        await handler.handle(message, USER_ID, "")
        message.reply.assert_called_once()
        reply_text = message.reply.call_args[0][0]
        assert "기본값" in reply_text
        assert "08:00" in reply_text
        assert "서울" in reply_text

    @pytest.mark.asyncio
    async def test_show_custom_settings(self, handler, message):
        """커스텀 설정 표시"""
        handler.db.briefing.get_settings = AsyncMock(return_value={
            "enabled": True,
            "time": "07:00",
            "city": "부산",
            "last_sent": "2026-02-13 07:00:00"
        })
        await handler.handle(message, USER_ID, "")
        reply_text = message.reply.call_args[0][0]
        assert "07:00" in reply_text
        assert "부산" in reply_text
        assert "활성화" in reply_text

    @pytest.mark.asyncio
    async def test_show_disabled_settings(self, handler, message):
        handler.db.briefing.get_settings = AsyncMock(return_value={
            "enabled": False,
            "time": "08:00",
            "city": "서울",
            "last_sent": None
        })
        await handler.handle(message, USER_ID, "")
        reply_text = message.reply.call_args[0][0]
        assert "비활성화" in reply_text


class TestBriefingHandleNow:
    """IMP-016: /briefing now 즉시 브리핑 명령어"""

    @pytest.mark.asyncio
    async def test_now_success_with_settings(self, handler, message):
        """설정된 도시로 즉시 브리핑 생성"""
        handler.db.briefing.get_settings = AsyncMock(return_value={"city": "부산"})
        with patch(
            "src.bot.handlers.briefing.generate_briefing",
            new=AsyncMock(return_value="부산 브리핑 내용"),
        ):
            await handler.handle(message, USER_ID, "now")
        message.reply.assert_called_once_with("부산 브리핑 내용")

    @pytest.mark.asyncio
    async def test_now_uses_default_city_when_no_settings(self, handler, message):
        """설정 없을 때 기본 도시(서울)로 브리핑 생성"""
        handler.db.briefing.get_settings = AsyncMock(return_value=None)
        mock_gen = AsyncMock(return_value="서울 브리핑")
        with patch("src.bot.handlers.briefing.generate_briefing", new=mock_gen):
            await handler.handle(message, USER_ID, "now")
        city_arg = mock_gen.call_args[0][0]
        assert city_arg == "서울"
        message.reply.assert_called_once_with("서울 브리핑")

    @pytest.mark.asyncio
    async def test_now_passes_user_id_and_reminder_to_generator(self, handler, message):
        """generate_briefing에 user_id와 db.reminder가 전달된다"""
        handler.db.briefing.get_settings = AsyncMock(return_value={"city": "인천"})
        mock_gen = AsyncMock(return_value="브리핑")
        with patch("src.bot.handlers.briefing.generate_briefing", new=mock_gen):
            await handler.handle(message, USER_ID, "now")
        mock_gen.assert_called_once_with("인천", USER_ID, handler.db.reminder)

    @pytest.mark.asyncio
    async def test_now_generate_failure_replies_error(self, handler, message):
        """generate_briefing 예외 시 에러 메시지를 응답한다"""
        handler.db.briefing.get_settings = AsyncMock(return_value={"city": "서울"})
        with patch(
            "src.bot.handlers.briefing.generate_briefing",
            new=AsyncMock(side_effect=Exception("API 오류")),
        ):
            await handler.handle(message, USER_ID, "now")
        message.reply.assert_called_once()
        assert "오류" in message.reply.call_args[0][0]

    @pytest.mark.asyncio
    async def test_now_whitespace_stripped(self, handler, message):
        """' now ' 처럼 공백이 있어도 정상 처리된다"""
        handler.db.briefing.get_settings = AsyncMock(return_value={"city": "서울"})
        with patch(
            "src.bot.handlers.briefing.generate_briefing",
            new=AsyncMock(return_value="브리핑"),
        ):
            await handler.handle(message, USER_ID, "  now  ")
        message.reply.assert_called_once_with("브리핑")


class TestBriefingHandleUnknown:
    @pytest.mark.asyncio
    async def test_unknown_args_shows_usage(self, handler, message):
        await handler.handle(message, USER_ID, "잘못된명령")
        reply_text = message.reply.call_args[0][0]
        assert "사용법" in reply_text
        assert "/briefing on" in reply_text

    @pytest.mark.asyncio
    async def test_usage_message_includes_now(self, handler, message):
        """사용법 메시지에 now 명령어가 포함된다 (IMP-016)"""
        await handler.handle(message, USER_ID, "잘못된명령")
        reply_text = message.reply.call_args[0][0]
        assert "now" in reply_text
