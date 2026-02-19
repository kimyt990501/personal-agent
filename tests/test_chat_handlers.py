"""Tests for Tool classes (memo, search, briefing) and ChatHandler._maybe_compress()."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.bot.handlers.chat import ChatHandler
from src.bot.tools import ToolContext
from src.bot.tools.memo import MemoTool
from src.bot.tools.search import SearchTool
from src.bot.tools.briefing import BriefingTool


USER_ID = "test_user_123"


@pytest.fixture
def mock_db():
    """Mock DB with async memo, conversation, persona, reminder sub-mocks."""
    db = MagicMock()
    db.memo = AsyncMock()
    db.conversation = AsyncMock()
    db.persona = AsyncMock()
    db.reminder = AsyncMock()
    return db


@pytest.fixture
def memo_tool():
    return MemoTool()


@pytest.fixture
def search_tool():
    return SearchTool()


@pytest.fixture
def briefing_tool():
    return BriefingTool()


def make_context(db):
    return ToolContext(user_id=USER_ID, db=db, persona={})


@pytest_asyncio.fixture
async def chat_handler(mock_db):
    """Create ChatHandler with mocked dependencies (for _maybe_compress tests)."""
    mock_llm = MagicMock()
    handler = ChatHandler(mock_db, mock_llm)
    return handler


# ─── MemoTool: MEMO_SAVE ───

class TestTryMemoSave:
    @pytest.mark.asyncio
    async def test_save_memo(self, memo_tool, mock_db):
        mock_db.memo.add = AsyncMock(return_value=1)
        context = make_context(mock_db)

        result = await memo_tool.try_execute("[MEMO_SAVE:우유 사기]", context)

        assert result is not None
        assert "저장 완료" in result
        assert "#1" in result
        assert "우유 사기" in result
        mock_db.memo.add.assert_called_once_with(USER_ID, "우유 사기")

    @pytest.mark.asyncio
    async def test_save_memo_strips_whitespace(self, memo_tool, mock_db):
        mock_db.memo.add = AsyncMock(return_value=5)
        context = make_context(mock_db)

        result = await memo_tool.try_execute("[MEMO_SAVE:  내용에 공백  ]", context)

        assert result is not None
        mock_db.memo.add.assert_called_once_with(USER_ID, "내용에 공백")


# ─── MemoTool: MEMO_LIST ───

class TestTryMemoList:
    @pytest.mark.asyncio
    async def test_list_memos(self, memo_tool, mock_db):
        mock_db.memo.get_all = AsyncMock(return_value=[
            {"id": 1, "content": "우유 사기", "created_at": "2026-02-13 10:00:00"},
            {"id": 2, "content": "회의 준비", "created_at": "2026-02-13 11:00:00"},
        ])
        context = make_context(mock_db)

        result = await memo_tool.try_execute("[MEMO_LIST]", context)

        assert result is not None
        assert "메모 목록" in result
        assert "우유 사기" in result
        assert "회의 준비" in result
        assert "#1" in result
        assert "#2" in result

    @pytest.mark.asyncio
    async def test_list_empty(self, memo_tool, mock_db):
        mock_db.memo.get_all = AsyncMock(return_value=[])
        context = make_context(mock_db)

        result = await memo_tool.try_execute("[MEMO_LIST]", context)

        assert result is not None
        assert "없습니다" in result


# ─── MemoTool: MEMO_SEARCH ───

class TestTryMemoSearch:
    @pytest.mark.asyncio
    async def test_search_found(self, memo_tool, mock_db):
        mock_db.memo.search = AsyncMock(return_value=[
            {"id": 1, "content": "우유 사기", "created_at": "2026-02-13 10:00:00"},
        ])
        context = make_context(mock_db)

        result = await memo_tool.try_execute("[MEMO_SEARCH:우유]", context)

        assert result is not None
        assert "우유" in result
        assert "검색 결과" in result
        mock_db.memo.search.assert_called_once_with(USER_ID, "우유")

    @pytest.mark.asyncio
    async def test_search_not_found(self, memo_tool, mock_db):
        mock_db.memo.search = AsyncMock(return_value=[])
        context = make_context(mock_db)

        result = await memo_tool.try_execute("[MEMO_SEARCH:없는키워드]", context)

        assert result is not None
        assert "검색 결과가 없습니다" in result


# ─── MemoTool: MEMO_DEL (position 기반 삭제) ───

class TestTryMemoDel:
    @pytest.mark.asyncio
    async def test_delete_by_position_success(self, memo_tool, mock_db):
        """position=1 → 목록의 첫 번째 메모(DB id=10) 삭제"""
        mock_db.memo.get_all = AsyncMock(return_value=[
            {"id": 10, "content": "첫 번째 메모", "created_at": "2026-02-13 12:00:00"},
            {"id": 5, "content": "두 번째 메모", "created_at": "2026-02-13 11:00:00"},
        ])
        mock_db.memo.delete = AsyncMock(return_value=True)
        context = make_context(mock_db)

        result = await memo_tool.try_execute("[MEMO_DEL:1]", context)

        assert result is not None
        assert "삭제 완료" in result
        assert "첫 번째 메모" in result
        mock_db.memo.delete.assert_called_once_with(USER_ID, 10)

    @pytest.mark.asyncio
    async def test_delete_by_position_second(self, memo_tool, mock_db):
        """position=2 → 목록의 두 번째 메모(DB id=5) 삭제"""
        mock_db.memo.get_all = AsyncMock(return_value=[
            {"id": 10, "content": "첫 번째", "created_at": "2026-02-13 12:00:00"},
            {"id": 5, "content": "두 번째", "created_at": "2026-02-13 11:00:00"},
        ])
        mock_db.memo.delete = AsyncMock(return_value=True)
        context = make_context(mock_db)

        result = await memo_tool.try_execute("[MEMO_DEL:2]", context)

        mock_db.memo.delete.assert_called_once_with(USER_ID, 5)

    @pytest.mark.asyncio
    async def test_delete_position_out_of_range(self, memo_tool, mock_db):
        """범위 밖 position → 에러 메시지"""
        mock_db.memo.get_all = AsyncMock(return_value=[
            {"id": 1, "content": "유일한 메모", "created_at": "2026-02-13 12:00:00"},
        ])
        context = make_context(mock_db)

        result = await memo_tool.try_execute("[MEMO_DEL:5]", context)

        assert result is not None
        assert "1개만 있습니다" in result
        assert "5번째" in result

    @pytest.mark.asyncio
    async def test_delete_position_zero(self, memo_tool, mock_db):
        """position=0 → 범위 밖 에러"""
        mock_db.memo.get_all = AsyncMock(return_value=[
            {"id": 1, "content": "메모", "created_at": "2026-02-13 12:00:00"},
        ])
        context = make_context(mock_db)

        result = await memo_tool.try_execute("[MEMO_DEL:0]", context)

        assert "찾을 수 없습니다" in result or "개만 있습니다" in result

    @pytest.mark.asyncio
    async def test_delete_empty_list(self, memo_tool, mock_db):
        """메모가 없는 상태에서 삭제 시도"""
        mock_db.memo.get_all = AsyncMock(return_value=[])
        context = make_context(mock_db)

        result = await memo_tool.try_execute("[MEMO_DEL:1]", context)

        assert result is not None
        assert "0개만 있습니다" in result

    @pytest.mark.asyncio
    async def test_delete_db_failure(self, memo_tool, mock_db):
        """DB에서 삭제 실패 (delete가 False 반환)"""
        mock_db.memo.get_all = AsyncMock(return_value=[
            {"id": 10, "content": "메모", "created_at": "2026-02-13 12:00:00"},
        ])
        mock_db.memo.delete = AsyncMock(return_value=False)
        context = make_context(mock_db)

        result = await memo_tool.try_execute("[MEMO_DEL:1]", context)

        assert "찾을 수 없습니다" in result


# ─── MemoTool: no match ───

class TestTryMemoNoMatch:
    @pytest.mark.asyncio
    async def test_no_memo_pattern(self, memo_tool, mock_db):
        context = make_context(mock_db)
        result = await memo_tool.try_execute("일반 텍스트 응답입니다.", context)
        assert result is None

    @pytest.mark.asyncio
    async def test_weather_pattern_not_detected(self, memo_tool, mock_db):
        context = make_context(mock_db)
        result = await memo_tool.try_execute("[WEATHER:서울]", context)
        assert result is None


# ─── SearchTool ───

class TestTrySearch:
    @pytest.mark.asyncio
    @patch("src.bot.tools.search.web_search")
    @patch("src.bot.tools.search.format_search_results")
    async def test_search_success(self, mock_format, mock_search, search_tool, mock_db):
        mock_search.return_value = [
            {"title": "비트코인", "body": "현재 시세...", "href": "https://example.com"},
        ]
        mock_format.return_value = "1. **비트코인**\n   현재 시세...\n   링크: https://example.com"
        context = make_context(mock_db)

        result = await search_tool.try_execute("[SEARCH:비트코인 시세]", context)

        assert result is not None
        assert "비트코인" in result
        assert "검색 결과" in result
        mock_search.assert_called_once_with("비트코인 시세")

    @pytest.mark.asyncio
    @patch("src.bot.tools.search.web_search")
    async def test_search_no_results(self, mock_search, search_tool, mock_db):
        mock_search.return_value = []
        context = make_context(mock_db)

        result = await search_tool.try_execute("[SEARCH:아무것도없는쿼리]", context)

        assert result is not None
        assert "가져오지 못했습니다" in result

    @pytest.mark.asyncio
    async def test_search_no_match(self, search_tool, mock_db):
        context = make_context(mock_db)
        result = await search_tool.try_execute("검색 없이 일반 응답", context)
        assert result is None

    @pytest.mark.asyncio
    @patch("src.bot.tools.search.web_search")
    @patch("src.bot.tools.search.format_search_results")
    async def test_search_strips_whitespace(self, mock_format, mock_search, search_tool, mock_db):
        mock_search.return_value = [{"title": "t", "body": "b", "href": "h"}]
        mock_format.return_value = "formatted"
        context = make_context(mock_db)

        await search_tool.try_execute("[SEARCH:  공백 포함 쿼리  ]", context)

        mock_search.assert_called_once_with("공백 포함 쿼리")


# ─── BriefingTool: BRIEFING_SET ───

class TestTryBriefingSet:
    @pytest.mark.asyncio
    async def test_set_time_valid(self, briefing_tool, mock_db):
        mock_db.briefing = AsyncMock()
        context = make_context(mock_db)
        result = await briefing_tool.try_execute("[BRIEFING_SET:time,07:00]", context)
        assert result is not None
        assert "07:00" in result
        mock_db.briefing.set_settings.assert_called_once_with(USER_ID, time="07:00")

    @pytest.mark.asyncio
    async def test_set_time_invalid_format(self, briefing_tool, mock_db):
        mock_db.briefing = AsyncMock()
        context = make_context(mock_db)
        result = await briefing_tool.try_execute("[BRIEFING_SET:time,오전7시]", context)
        assert "형식" in result
        mock_db.briefing.set_settings.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_time_out_of_range(self, briefing_tool, mock_db):
        """BUG-006 수정 확인: 25:99 같은 범위 밖 시간 거부"""
        mock_db.briefing = AsyncMock()
        context = make_context(mock_db)
        result = await briefing_tool.try_execute("[BRIEFING_SET:time,25:99]", context)
        assert "올바르지 않습니다" in result
        mock_db.briefing.set_settings.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_time_boundary_valid(self, briefing_tool, mock_db):
        """23:59 — 최대 유효 시간"""
        mock_db.briefing = AsyncMock()
        context = make_context(mock_db)
        result = await briefing_tool.try_execute("[BRIEFING_SET:time,23:59]", context)
        assert "23:59" in result
        mock_db.briefing.set_settings.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_time_boundary_zero(self, briefing_tool, mock_db):
        """00:00 — 최소 유효 시간"""
        mock_db.briefing = AsyncMock()
        context = make_context(mock_db)
        result = await briefing_tool.try_execute("[BRIEFING_SET:time,00:00]", context)
        assert "00:00" in result

    @pytest.mark.asyncio
    async def test_set_city(self, briefing_tool, mock_db):
        mock_db.briefing = AsyncMock()
        context = make_context(mock_db)
        result = await briefing_tool.try_execute("[BRIEFING_SET:city,부산]", context)
        assert "부산" in result
        mock_db.briefing.set_settings.assert_called_once_with(USER_ID, city="부산")

    @pytest.mark.asyncio
    async def test_set_enabled_true(self, briefing_tool, mock_db):
        mock_db.briefing = AsyncMock()
        context = make_context(mock_db)
        result = await briefing_tool.try_execute("[BRIEFING_SET:enabled,true]", context)
        assert "활성화" in result
        mock_db.briefing.set_settings.assert_called_once_with(USER_ID, enabled=True)

    @pytest.mark.asyncio
    async def test_set_enabled_false(self, briefing_tool, mock_db):
        mock_db.briefing = AsyncMock()
        context = make_context(mock_db)
        result = await briefing_tool.try_execute("[BRIEFING_SET:enabled,false]", context)
        assert "비활성화" in result
        mock_db.briefing.set_settings.assert_called_once_with(USER_ID, enabled=False)

    @pytest.mark.asyncio
    async def test_set_enabled_off(self, briefing_tool, mock_db):
        """'off' 문자열도 비활성화로 처리"""
        mock_db.briefing = AsyncMock()
        context = make_context(mock_db)
        result = await briefing_tool.try_execute("[BRIEFING_SET:enabled,off]", context)
        assert "비활성화" in result

    @pytest.mark.asyncio
    async def test_set_unknown_key(self, briefing_tool, mock_db):
        mock_db.briefing = AsyncMock()
        context = make_context(mock_db)
        result = await briefing_tool.try_execute("[BRIEFING_SET:unknown,value]", context)
        assert "알 수 없는" in result


# ─── BriefingTool: BRIEFING_GET ───

class TestTryBriefingGet:
    @pytest.mark.asyncio
    async def test_get_default_settings(self, briefing_tool, mock_db):
        mock_db.briefing = AsyncMock()
        mock_db.briefing.get_settings = AsyncMock(return_value=None)
        context = make_context(mock_db)
        result = await briefing_tool.try_execute("[BRIEFING_GET]", context)
        assert "기본값" in result
        assert "08:00" in result
        assert "서울" in result

    @pytest.mark.asyncio
    async def test_get_custom_settings(self, briefing_tool, mock_db):
        mock_db.briefing = AsyncMock()
        mock_db.briefing.get_settings = AsyncMock(return_value={
            "enabled": True,
            "time": "07:00",
            "city": "부산",
            "last_sent": "2026-02-14 07:00:00"
        })
        context = make_context(mock_db)
        result = await briefing_tool.try_execute("[BRIEFING_GET]", context)
        assert "07:00" in result
        assert "부산" in result
        assert "활성화" in result

    @pytest.mark.asyncio
    async def test_get_disabled_settings(self, briefing_tool, mock_db):
        mock_db.briefing = AsyncMock()
        mock_db.briefing.get_settings = AsyncMock(return_value={
            "enabled": False,
            "time": "08:00",
            "city": "서울",
            "last_sent": None
        })
        context = make_context(mock_db)
        result = await briefing_tool.try_execute("[BRIEFING_GET]", context)
        assert "비활성화" in result


# ─── BriefingTool: no match ───

class TestTryBriefingNoMatch:
    @pytest.mark.asyncio
    async def test_no_briefing_pattern(self, briefing_tool, mock_db):
        mock_db.briefing = AsyncMock()
        context = make_context(mock_db)
        result = await briefing_tool.try_execute("일반 응답입니다.", context)
        assert result is None

    @pytest.mark.asyncio
    async def test_memo_pattern_not_detected(self, briefing_tool, mock_db):
        mock_db.briefing = AsyncMock()
        context = make_context(mock_db)
        result = await briefing_tool.try_execute("[MEMO_LIST]", context)
        assert result is None


# ─── _maybe_compress ───

class TestMaybeCompress:
    @pytest.mark.asyncio
    async def test_no_compress_below_threshold(self, chat_handler):
        """메시지 수가 임계값 이하면 압축하지 않는다."""
        chat_handler.db.conversation.get_message_count = AsyncMock(return_value=15)
        chat_handler.ollama = AsyncMock()

        with patch("src.config.SUMMARY_THRESHOLD", 20):
            await chat_handler._maybe_compress(USER_ID, {})

        chat_handler.ollama.chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_compress_triggered_above_threshold(self, chat_handler):
        """메시지 수가 임계값 초과 시 압축이 실행된다."""
        messages = [{"role": "user", "content": f"메시지 {i}"} for i in range(22)]
        chat_handler.db.conversation.get_message_count = AsyncMock(return_value=22)
        chat_handler.db.conversation.get_all_messages = AsyncMock(return_value=messages)
        chat_handler.db.conversation.get_summary = AsyncMock(return_value=None)
        chat_handler.db.conversation.save_summary = AsyncMock()
        chat_handler.db.conversation.delete_old_messages = AsyncMock()

        mock_ollama = AsyncMock()
        mock_ollama.chat = AsyncMock(return_value="새로운 요약 텍스트")
        chat_handler.ollama = mock_ollama

        with patch("src.config.SUMMARY_THRESHOLD", 20), \
             patch("src.config.SUMMARY_KEEP_RECENT", 10):
            await chat_handler._maybe_compress(USER_ID, {})

        mock_ollama.chat.assert_called_once()
        chat_handler.db.conversation.save_summary.assert_called_once_with(
            USER_ID, "새로운 요약 텍스트", 12
        )
        chat_handler.db.conversation.delete_old_messages.assert_called_once_with(USER_ID, 10)

    @pytest.mark.asyncio
    async def test_compress_with_existing_summary(self, chat_handler):
        """기존 요약이 있을 때 통합 요약 프롬프트를 사용한다."""
        messages = [{"role": "user", "content": f"메시지 {i}"} for i in range(22)]
        chat_handler.db.conversation.get_message_count = AsyncMock(return_value=22)
        chat_handler.db.conversation.get_all_messages = AsyncMock(return_value=messages)
        chat_handler.db.conversation.get_summary = AsyncMock(return_value="기존 요약 내용")
        chat_handler.db.conversation.save_summary = AsyncMock()
        chat_handler.db.conversation.delete_old_messages = AsyncMock()

        mock_ollama = AsyncMock()
        mock_ollama.chat = AsyncMock(return_value="통합 요약")
        chat_handler.ollama = mock_ollama

        with patch("src.config.SUMMARY_THRESHOLD", 20), \
             patch("src.config.SUMMARY_KEEP_RECENT", 10):
            await chat_handler._maybe_compress(USER_ID, {})

        call_args = mock_ollama.chat.call_args
        prompt = call_args[0][0][0]["content"]
        assert "기존 요약" in prompt
        assert "기존 요약 내용" in prompt

    @pytest.mark.asyncio
    async def test_compress_failure_does_not_delete_messages(self, chat_handler):
        """요약 LLM 호출 실패 시 메시지를 삭제하지 않는다."""
        messages = [{"role": "user", "content": f"메시지 {i}"} for i in range(22)]
        chat_handler.db.conversation.get_message_count = AsyncMock(return_value=22)
        chat_handler.db.conversation.get_all_messages = AsyncMock(return_value=messages)
        chat_handler.db.conversation.get_summary = AsyncMock(return_value=None)
        chat_handler.db.conversation.save_summary = AsyncMock()
        chat_handler.db.conversation.delete_old_messages = AsyncMock()

        mock_ollama = AsyncMock()
        mock_ollama.chat = AsyncMock(side_effect=Exception("LLM 에러"))
        chat_handler.ollama = mock_ollama

        with patch("src.config.SUMMARY_THRESHOLD", 20), \
             patch("src.config.SUMMARY_KEEP_RECENT", 10):
            await chat_handler._maybe_compress(USER_ID, {})  # should not raise

        chat_handler.db.conversation.delete_old_messages.assert_not_called()
        chat_handler.db.conversation.save_summary.assert_not_called()

    @pytest.mark.asyncio
    async def test_compress_exact_threshold_not_triggered(self, chat_handler):
        """메시지 수가 임계값과 정확히 같으면 압축하지 않는다."""
        chat_handler.db.conversation.get_message_count = AsyncMock(return_value=20)
        chat_handler.ollama = AsyncMock()

        with patch("src.config.SUMMARY_THRESHOLD", 20):
            await chat_handler._maybe_compress(USER_ID, {})

        chat_handler.ollama.chat.assert_not_called()
