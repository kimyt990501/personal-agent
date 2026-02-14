"""Tests for src/db/ - Database layer tests with temporary SQLite"""
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
import pytest_asyncio

from src.db.memo import MemoDB
from src.db.conversation import ConversationDB
from src.db.persona import PersonaDB
from src.db.reminder import ReminderDB


USER_ID = "test_user_123"


# ─── MemoDB ───

class TestMemoDB:
    @pytest_asyncio.fixture
    async def memo_db(self, tmp_db):
        db = MemoDB()
        db.db_path = tmp_db
        return db

    @pytest.mark.asyncio
    async def test_add_and_get_all(self, memo_db):
        memo_id = await memo_db.add(USER_ID, "테스트 메모 1")
        assert isinstance(memo_id, int)
        assert memo_id > 0

        memos = await memo_db.get_all(USER_ID)
        assert len(memos) == 1
        assert memos[0]["content"] == "테스트 메모 1"
        assert memos[0]["id"] == memo_id

    @pytest.mark.asyncio
    async def test_add_multiple_and_count(self, memo_db):
        """여러 메모를 추가하면 모두 반환되어야 함"""
        await memo_db.add(USER_ID, "첫 번째")
        await memo_db.add(USER_ID, "두 번째")
        await memo_db.add(USER_ID, "세 번째")

        memos = await memo_db.get_all(USER_ID)
        assert len(memos) == 3
        contents = {m["content"] for m in memos}
        assert contents == {"첫 번째", "두 번째", "세 번째"}

    @pytest.mark.asyncio
    async def test_order_with_id_tiebreaker(self, memo_db):
        """[BUG-001 FIXED] ORDER BY created_at DESC, id DESC 로 수정됨.
        동일 초 내 삽입 시에도 최신(높은 id)이 먼저 나와야 함."""
        id1 = await memo_db.add(USER_ID, "첫 번째")
        id2 = await memo_db.add(USER_ID, "두 번째")

        memos = await memo_db.get_all(USER_ID)
        assert len(memos) == 2
        # id DESC이므로 id2(두 번째)가 먼저 나옴
        assert memos[0]["id"] == id2
        assert memos[0]["content"] == "두 번째"
        assert memos[1]["id"] == id1
        assert memos[1]["content"] == "첫 번째"

    @pytest.mark.asyncio
    async def test_get_all_with_limit(self, memo_db):
        for i in range(5):
            await memo_db.add(USER_ID, f"메모 {i}")

        memos = await memo_db.get_all(USER_ID, limit=3)
        assert len(memos) == 3

    @pytest.mark.asyncio
    async def test_delete(self, memo_db):
        memo_id = await memo_db.add(USER_ID, "삭제할 메모")
        deleted = await memo_db.delete(USER_ID, memo_id)
        assert deleted is True

        memos = await memo_db.get_all(USER_ID)
        assert len(memos) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, memo_db):
        deleted = await memo_db.delete(USER_ID, 9999)
        assert deleted is False

    @pytest.mark.asyncio
    async def test_delete_wrong_user(self, memo_db):
        """다른 유저의 메모는 삭제할 수 없음"""
        memo_id = await memo_db.add(USER_ID, "내 메모")
        deleted = await memo_db.delete("other_user", memo_id)
        assert deleted is False

    @pytest.mark.asyncio
    async def test_search(self, memo_db):
        await memo_db.add(USER_ID, "점심 약속 내일 12시")
        await memo_db.add(USER_ID, "저녁 약속 금요일")
        await memo_db.add(USER_ID, "프로젝트 마감일")

        results = await memo_db.search(USER_ID, "약속")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_no_results(self, memo_db):
        await memo_db.add(USER_ID, "테스트 메모")
        results = await memo_db.search(USER_ID, "존재하지않는키워드")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_user_isolation(self, memo_db):
        """다른 유저의 메모는 보이지 않아야 함"""
        await memo_db.add("user_a", "A의 메모")
        await memo_db.add("user_b", "B의 메모")

        memos_a = await memo_db.get_all("user_a")
        assert len(memos_a) == 1
        assert memos_a[0]["content"] == "A의 메모"


# ─── ConversationDB ───

class TestConversationDB:
    @pytest_asyncio.fixture
    async def conv_db(self, tmp_db):
        db = ConversationDB()
        db.db_path = tmp_db
        return db

    @pytest.mark.asyncio
    async def test_add_and_get_history(self, conv_db):
        await conv_db.add_message(USER_ID, "user", "안녕하세요")
        await conv_db.add_message(USER_ID, "assistant", "안녕하세요!")

        history = await conv_db.get_history(USER_ID)
        assert len(history) == 2
        roles = {h["role"] for h in history}
        assert roles == {"user", "assistant"}

    @pytest.mark.asyncio
    async def test_history_order_fixed(self, conv_db):
        """[BUG-001 FIXED] ORDER BY created_at DESC, id DESC + reversed()
        동일 초 내 메시지도 시간순 보장됨."""
        await conv_db.add_message(USER_ID, "user", "첫 번째")
        await conv_db.add_message(USER_ID, "assistant", "두 번째")
        await conv_db.add_message(USER_ID, "user", "세 번째")

        history = await conv_db.get_history(USER_ID)
        assert len(history) == 3
        # reversed()로 ASC 순으로 반환되므로 순서 보장
        assert history[0]["content"] == "첫 번째"
        assert history[1]["content"] == "두 번째"
        assert history[2]["content"] == "세 번째"

    @pytest.mark.asyncio
    async def test_history_limit(self, conv_db):
        for i in range(10):
            await conv_db.add_message(USER_ID, "user", f"메시지 {i}")

        history = await conv_db.get_history(USER_ID, limit=5)
        assert len(history) == 5

    @pytest.mark.asyncio
    async def test_clear_history(self, conv_db):
        await conv_db.add_message(USER_ID, "user", "테스트")
        await conv_db.clear_history(USER_ID)

        history = await conv_db.get_history(USER_ID)
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_clear_only_affects_target_user(self, conv_db):
        await conv_db.add_message("user_a", "user", "A 메시지")
        await conv_db.add_message("user_b", "user", "B 메시지")

        await conv_db.clear_history("user_a")

        history_a = await conv_db.get_history("user_a")
        history_b = await conv_db.get_history("user_b")
        assert len(history_a) == 0
        assert len(history_b) == 1


# ─── PersonaDB ───

class TestPersonaDB:
    @pytest_asyncio.fixture
    async def persona_db(self, tmp_db):
        db = PersonaDB()
        db.db_path = tmp_db
        return db

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, persona_db):
        result = await persona_db.get(USER_ID)
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get(self, persona_db):
        await persona_db.set(USER_ID, "뽀삐", "개인 비서", "친근한 반말")
        persona = await persona_db.get(USER_ID)

        assert persona is not None
        assert persona["name"] == "뽀삐"
        assert persona["role"] == "개인 비서"
        assert persona["tone"] == "친근한 반말"

    @pytest.mark.asyncio
    async def test_update_existing(self, persona_db):
        """같은 유저에 대해 set을 다시 호출하면 업데이트"""
        await persona_db.set(USER_ID, "뽀삐", "비서", "반말")
        await persona_db.set(USER_ID, "쿠키", "친구", "존댓말")

        persona = await persona_db.get(USER_ID)
        assert persona["name"] == "쿠키"
        assert persona["role"] == "친구"

    @pytest.mark.asyncio
    async def test_clear(self, persona_db):
        await persona_db.set(USER_ID, "뽀삐", "비서", "반말")
        await persona_db.clear(USER_ID)

        persona = await persona_db.get(USER_ID)
        assert persona is None


# ─── ReminderDB ───

class TestReminderDB:
    @pytest_asyncio.fixture
    async def reminder_db(self, tmp_db):
        db = ReminderDB()
        db.db_path = tmp_db
        return db

    @pytest.mark.asyncio
    async def test_add_and_get_all(self, reminder_db):
        remind_at = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        reminder_id = await reminder_db.add(USER_ID, "회의 참석", remind_at)

        assert isinstance(reminder_id, int)

        reminders = await reminder_db.get_all(USER_ID)
        assert len(reminders) == 1
        assert reminders[0]["content"] == "회의 참석"

    @pytest.mark.asyncio
    async def test_add_with_recurrence(self, reminder_db):
        remind_at = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        await reminder_db.add(USER_ID, "매일 운동", remind_at, recurrence="daily")

        reminders = await reminder_db.get_all(USER_ID)
        assert reminders[0]["recurrence"] == "daily"

    @pytest.mark.asyncio
    async def test_delete(self, reminder_db):
        remind_at = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        rid = await reminder_db.add(USER_ID, "삭제할 리마인더", remind_at)

        deleted = await reminder_db.delete(USER_ID, rid)
        assert deleted is True

        reminders = await reminder_db.get_all(USER_ID)
        assert len(reminders) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, reminder_db):
        deleted = await reminder_db.delete(USER_ID, 9999)
        assert deleted is False

    @pytest.mark.asyncio
    async def test_delete_by_id(self, reminder_db):
        remind_at = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        rid = await reminder_db.add(USER_ID, "알림", remind_at)

        await reminder_db.delete_by_id(rid)

        reminders = await reminder_db.get_all(USER_ID)
        assert len(reminders) == 0

    @pytest.mark.asyncio
    async def test_reschedule(self, reminder_db):
        remind_at = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        rid = await reminder_db.add(USER_ID, "재스케줄링", remind_at, recurrence="daily")

        new_time = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        await reminder_db.reschedule(rid, new_time)

        reminders = await reminder_db.get_all(USER_ID)
        assert reminders[0]["remind_at"] == new_time

    @pytest.mark.asyncio
    async def test_get_due(self, reminder_db):
        """만료된 리마인더만 get_due로 가져와야 함"""
        past = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        future = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")

        await reminder_db.add(USER_ID, "만료됨", past)
        await reminder_db.add(USER_ID, "아직 안됨", future)

        due = await reminder_db.get_due()
        assert len(due) == 1
        assert due[0]["content"] == "만료됨"


# ─── ReminderDB: static methods ───

class TestReminderDBStaticMethods:
    def test_calc_next_daily(self):
        result = ReminderDB.calc_next("2026-02-13 09:00:00", "daily")
        assert result == "2026-02-14 09:00:00"

    def test_calc_next_weekday_from_friday(self):
        """금요일 -> 다음 월요일 (주말 건너뛰기)"""
        result = ReminderDB.calc_next("2026-02-13 09:00:00", "weekday")  # 금요일
        assert result == "2026-02-16 09:00:00"  # 월요일

    def test_calc_next_weekday_from_monday(self):
        """월요일 -> 화요일"""
        result = ReminderDB.calc_next("2026-02-16 09:00:00", "weekday")  # 월요일
        assert result == "2026-02-17 09:00:00"  # 화요일

    def test_calc_next_weekly(self):
        result = ReminderDB.calc_next("2026-02-13 09:00:00", "weekly:4")
        assert result == "2026-02-20 09:00:00"

    def test_calc_next_unknown_falls_back_to_daily(self):
        result = ReminderDB.calc_next("2026-02-13 09:00:00", "unknown")
        assert result == "2026-02-14 09:00:00"

    def test_recurrence_label_daily(self):
        assert ReminderDB.recurrence_label("daily") == "매일"

    def test_recurrence_label_weekday(self):
        assert ReminderDB.recurrence_label("weekday") == "평일"

    def test_recurrence_label_weekly(self):
        label = ReminderDB.recurrence_label("weekly:0")
        assert "월" in label

    def test_recurrence_label_none(self):
        assert ReminderDB.recurrence_label(None) == ""

    def test_recurrence_label_unknown(self):
        assert ReminderDB.recurrence_label("custom") == "custom"
