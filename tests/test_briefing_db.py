"""Tests for BriefingDB - daily briefing settings CRUD."""

import pytest
import pytest_asyncio

from src.db.briefing import BriefingDB


USER_ID = "test_user_123"
USER_ID_2 = "test_user_456"


@pytest_asyncio.fixture
async def briefing_db(tmp_db):
    db = BriefingDB()
    db.db_path = tmp_db
    return db


class TestBriefingDBGetSettings:
    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, briefing_db):
        result = await briefing_db.get_settings(USER_ID)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_after_set(self, briefing_db):
        await briefing_db.set_settings(USER_ID)
        result = await briefing_db.get_settings(USER_ID)
        assert result is not None
        assert result["enabled"] is True
        assert result["time"] == "08:00"
        assert result["city"] == "서울"
        assert result["last_sent"] is None


class TestBriefingDBSetSettings:
    @pytest.mark.asyncio
    async def test_set_defaults(self, briefing_db):
        """기본값으로 생성"""
        await briefing_db.set_settings(USER_ID)
        result = await briefing_db.get_settings(USER_ID)
        assert result["enabled"] is True
        assert result["time"] == "08:00"
        assert result["city"] == "서울"

    @pytest.mark.asyncio
    async def test_set_custom_time(self, briefing_db):
        await briefing_db.set_settings(USER_ID, time="07:00")
        result = await briefing_db.get_settings(USER_ID)
        assert result["time"] == "07:00"

    @pytest.mark.asyncio
    async def test_set_custom_city(self, briefing_db):
        await briefing_db.set_settings(USER_ID, city="부산")
        result = await briefing_db.get_settings(USER_ID)
        assert result["city"] == "부산"

    @pytest.mark.asyncio
    async def test_set_disabled(self, briefing_db):
        await briefing_db.set_settings(USER_ID, enabled=False)
        result = await briefing_db.get_settings(USER_ID)
        assert result["enabled"] is False

    @pytest.mark.asyncio
    async def test_update_existing_settings(self, briefing_db):
        """기존 설정을 업데이트할 때 다른 필드 유지"""
        await briefing_db.set_settings(USER_ID, city="대전", time="07:30")
        # 시간만 변경
        await briefing_db.set_settings(USER_ID, time="09:00")
        result = await briefing_db.get_settings(USER_ID)
        assert result["time"] == "09:00"
        assert result["city"] == "대전"  # 도시는 유지

    @pytest.mark.asyncio
    async def test_set_multiple_kwargs(self, briefing_db):
        await briefing_db.set_settings(USER_ID, enabled=False, time="06:00", city="인천")
        result = await briefing_db.get_settings(USER_ID)
        assert result["enabled"] is False
        assert result["time"] == "06:00"
        assert result["city"] == "인천"


class TestBriefingDBUpdateLastSent:
    @pytest.mark.asyncio
    async def test_update_last_sent(self, briefing_db):
        await briefing_db.set_settings(USER_ID)
        await briefing_db.update_last_sent(USER_ID, "2026-02-13 08:00:00")
        result = await briefing_db.get_settings(USER_ID)
        assert result["last_sent"] == "2026-02-13 08:00:00"

    @pytest.mark.asyncio
    async def test_update_last_sent_nonexistent_user(self, briefing_db):
        """존재하지 않는 유저의 last_sent 업데이트 → 에러 없이 무시"""
        await briefing_db.update_last_sent("nonexistent", "2026-02-13 08:00:00")
        result = await briefing_db.get_settings("nonexistent")
        assert result is None  # 설정 자체가 없으므로 None


class TestBriefingDBGetAllEnabled:
    @pytest.mark.asyncio
    async def test_empty_db(self, briefing_db):
        result = await briefing_db.get_all_enabled()
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_only_enabled(self, briefing_db):
        await briefing_db.set_settings(USER_ID, enabled=True, city="서울")
        await briefing_db.set_settings(USER_ID_2, enabled=False, city="부산")
        result = await briefing_db.get_all_enabled()
        assert len(result) == 1
        assert result[0]["user_id"] == USER_ID

    @pytest.mark.asyncio
    async def test_returns_all_enabled(self, briefing_db):
        await briefing_db.set_settings(USER_ID, enabled=True)
        await briefing_db.set_settings(USER_ID_2, enabled=True)
        result = await briefing_db.get_all_enabled()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_result_fields(self, briefing_db):
        await briefing_db.set_settings(USER_ID, city="대구", time="09:00")
        result = await briefing_db.get_all_enabled()
        assert len(result) == 1
        item = result[0]
        assert item["user_id"] == USER_ID
        assert item["time"] == "09:00"
        assert item["city"] == "대구"
        assert "last_sent" in item


class TestBriefingDBUserIsolation:
    @pytest.mark.asyncio
    async def test_different_users_independent(self, briefing_db):
        """유저간 설정 독립성"""
        await briefing_db.set_settings(USER_ID, city="서울", time="08:00")
        await briefing_db.set_settings(USER_ID_2, city="부산", time="07:00")

        r1 = await briefing_db.get_settings(USER_ID)
        r2 = await briefing_db.get_settings(USER_ID_2)

        assert r1["city"] == "서울"
        assert r2["city"] == "부산"
        assert r1["time"] == "08:00"
        assert r2["time"] == "07:00"
