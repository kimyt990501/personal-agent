"""Tests for ChatHandler._try_memo() and _try_search() methods.
These test the new Tool Calling features added for memo and web search.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.bot.handlers.chat import ChatHandler


USER_ID = "test_user_123"


@pytest_asyncio.fixture
async def chat_handler():
    """Create ChatHandler with mocked dependencies."""
    mock_db = MagicMock()
    mock_db.memo = AsyncMock()
    mock_db.conversation = AsyncMock()
    mock_db.persona = AsyncMock()
    mock_db.reminder = AsyncMock()

    mock_llm = MagicMock()
    handler = ChatHandler(mock_db, mock_llm)
    return handler


# ─── _try_memo: MEMO_SAVE ───

class TestTryMemoSave:
    @pytest.mark.asyncio
    async def test_save_memo(self, chat_handler):
        chat_handler.db.memo.add = AsyncMock(return_value=1)

        result = await chat_handler._try_memo("[MEMO_SAVE:우유 사기]", USER_ID)

        assert result is not None
        assert "저장 완료" in result
        assert "#1" in result
        assert "우유 사기" in result
        chat_handler.db.memo.add.assert_called_once_with(USER_ID, "우유 사기")

    @pytest.mark.asyncio
    async def test_save_memo_strips_whitespace(self, chat_handler):
        chat_handler.db.memo.add = AsyncMock(return_value=5)

        result = await chat_handler._try_memo("[MEMO_SAVE:  내용에 공백  ]", USER_ID)

        assert result is not None
        chat_handler.db.memo.add.assert_called_once_with(USER_ID, "내용에 공백")


# ─── _try_memo: MEMO_LIST ───

class TestTryMemoList:
    @pytest.mark.asyncio
    async def test_list_memos(self, chat_handler):
        chat_handler.db.memo.get_all = AsyncMock(return_value=[
            {"id": 1, "content": "우유 사기", "created_at": "2026-02-13 10:00:00"},
            {"id": 2, "content": "회의 준비", "created_at": "2026-02-13 11:00:00"},
        ])

        result = await chat_handler._try_memo("[MEMO_LIST]", USER_ID)

        assert result is not None
        assert "메모 목록" in result
        assert "우유 사기" in result
        assert "회의 준비" in result
        assert "#1" in result
        assert "#2" in result

    @pytest.mark.asyncio
    async def test_list_empty(self, chat_handler):
        chat_handler.db.memo.get_all = AsyncMock(return_value=[])

        result = await chat_handler._try_memo("[MEMO_LIST]", USER_ID)

        assert result is not None
        assert "없습니다" in result


# ─── _try_memo: MEMO_SEARCH ───

class TestTryMemoSearch:
    @pytest.mark.asyncio
    async def test_search_found(self, chat_handler):
        chat_handler.db.memo.search = AsyncMock(return_value=[
            {"id": 1, "content": "우유 사기", "created_at": "2026-02-13 10:00:00"},
        ])

        result = await chat_handler._try_memo("[MEMO_SEARCH:우유]", USER_ID)

        assert result is not None
        assert "우유" in result
        assert "검색 결과" in result
        chat_handler.db.memo.search.assert_called_once_with(USER_ID, "우유")

    @pytest.mark.asyncio
    async def test_search_not_found(self, chat_handler):
        chat_handler.db.memo.search = AsyncMock(return_value=[])

        result = await chat_handler._try_memo("[MEMO_SEARCH:없는키워드]", USER_ID)

        assert result is not None
        assert "검색 결과가 없습니다" in result


# ─── _try_memo: MEMO_DEL (position 기반 삭제) ───

class TestTryMemoDel:
    @pytest.mark.asyncio
    async def test_delete_by_position_success(self, chat_handler):
        """position=1 → 목록의 첫 번째 메모(DB id=10) 삭제"""
        chat_handler.db.memo.get_all = AsyncMock(return_value=[
            {"id": 10, "content": "첫 번째 메모", "created_at": "2026-02-13 12:00:00"},
            {"id": 5, "content": "두 번째 메모", "created_at": "2026-02-13 11:00:00"},
        ])
        chat_handler.db.memo.delete = AsyncMock(return_value=True)

        result = await chat_handler._try_memo("[MEMO_DEL:1]", USER_ID)

        assert result is not None
        assert "삭제 완료" in result
        assert "첫 번째 메모" in result
        chat_handler.db.memo.delete.assert_called_once_with(USER_ID, 10)

    @pytest.mark.asyncio
    async def test_delete_by_position_second(self, chat_handler):
        """position=2 → 목록의 두 번째 메모(DB id=5) 삭제"""
        chat_handler.db.memo.get_all = AsyncMock(return_value=[
            {"id": 10, "content": "첫 번째", "created_at": "2026-02-13 12:00:00"},
            {"id": 5, "content": "두 번째", "created_at": "2026-02-13 11:00:00"},
        ])
        chat_handler.db.memo.delete = AsyncMock(return_value=True)

        result = await chat_handler._try_memo("[MEMO_DEL:2]", USER_ID)

        chat_handler.db.memo.delete.assert_called_once_with(USER_ID, 5)

    @pytest.mark.asyncio
    async def test_delete_position_out_of_range(self, chat_handler):
        """범위 밖 position → 에러 메시지"""
        chat_handler.db.memo.get_all = AsyncMock(return_value=[
            {"id": 1, "content": "유일한 메모", "created_at": "2026-02-13 12:00:00"},
        ])

        result = await chat_handler._try_memo("[MEMO_DEL:5]", USER_ID)

        assert result is not None
        assert "1개만 있습니다" in result
        assert "5번째" in result

    @pytest.mark.asyncio
    async def test_delete_position_zero(self, chat_handler):
        """position=0 → 범위 밖 에러"""
        chat_handler.db.memo.get_all = AsyncMock(return_value=[
            {"id": 1, "content": "메모", "created_at": "2026-02-13 12:00:00"},
        ])

        result = await chat_handler._try_memo("[MEMO_DEL:0]", USER_ID)

        assert "찾을 수 없습니다" in result or "개만 있습니다" in result

    @pytest.mark.asyncio
    async def test_delete_empty_list(self, chat_handler):
        """메모가 없는 상태에서 삭제 시도"""
        chat_handler.db.memo.get_all = AsyncMock(return_value=[])

        result = await chat_handler._try_memo("[MEMO_DEL:1]", USER_ID)

        assert result is not None
        assert "0개만 있습니다" in result

    @pytest.mark.asyncio
    async def test_delete_db_failure(self, chat_handler):
        """DB에서 삭제 실패 (delete가 False 반환)"""
        chat_handler.db.memo.get_all = AsyncMock(return_value=[
            {"id": 10, "content": "메모", "created_at": "2026-02-13 12:00:00"},
        ])
        chat_handler.db.memo.delete = AsyncMock(return_value=False)

        result = await chat_handler._try_memo("[MEMO_DEL:1]", USER_ID)

        assert "찾을 수 없습니다" in result


# ─── _try_memo: no match ───

class TestTryMemoNoMatch:
    @pytest.mark.asyncio
    async def test_no_memo_pattern(self, chat_handler):
        result = await chat_handler._try_memo("일반 텍스트 응답입니다.", USER_ID)
        assert result is None

    @pytest.mark.asyncio
    async def test_weather_pattern_not_detected(self, chat_handler):
        result = await chat_handler._try_memo("[WEATHER:서울]", USER_ID)
        assert result is None


# ─── _try_search ───

class TestTrySearch:
    @pytest.mark.asyncio
    @patch("src.bot.handlers.chat.web_search")
    @patch("src.bot.handlers.chat.format_search_results")
    async def test_search_success(self, mock_format, mock_search, chat_handler):
        mock_search.return_value = [
            {"title": "비트코인", "body": "현재 시세...", "href": "https://example.com"},
        ]
        mock_format.return_value = "1. **비트코인**\n   현재 시세...\n   링크: https://example.com"

        result = await chat_handler._try_search("[SEARCH:비트코인 시세]")

        assert result is not None
        assert "비트코인" in result
        assert "검색 결과" in result
        mock_search.assert_called_once_with("비트코인 시세")

    @pytest.mark.asyncio
    @patch("src.bot.handlers.chat.web_search")
    async def test_search_no_results(self, mock_search, chat_handler):
        mock_search.return_value = []

        result = await chat_handler._try_search("[SEARCH:아무것도없는쿼리]")

        assert result is not None
        assert "가져오지 못했습니다" in result

    @pytest.mark.asyncio
    async def test_search_no_match(self, chat_handler):
        result = await chat_handler._try_search("검색 없이 일반 응답")
        assert result is None

    @pytest.mark.asyncio
    @patch("src.bot.handlers.chat.web_search")
    @patch("src.bot.handlers.chat.format_search_results")
    async def test_search_strips_whitespace(self, mock_format, mock_search, chat_handler):
        mock_search.return_value = [{"title": "t", "body": "b", "href": "h"}]
        mock_format.return_value = "formatted"

        await chat_handler._try_search("[SEARCH:  공백 포함 쿼리  ]")

        mock_search.assert_called_once_with("공백 포함 쿼리")
