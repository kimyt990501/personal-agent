"""Tests for src/utils/time_parser.py"""
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from src.utils.time_parser import parse_time, format_datetime, validate_time_format


# ─── parse_time: 상대 시간 ───

class TestParseTimeRelative:
    """상대 시간 표현 파싱 테스트"""

    @patch("src.utils.time_parser.datetime")
    def test_minutes(self, mock_dt):
        now = datetime(2026, 2, 13, 10, 0, 0)
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)

        result = parse_time("30분")
        assert result == now + timedelta(minutes=30)

    @patch("src.utils.time_parser.datetime")
    def test_minutes_with_suffix(self, mock_dt):
        now = datetime(2026, 2, 13, 10, 0, 0)
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)

        result = parse_time("30분 후")
        assert result == now + timedelta(minutes=30)

    @patch("src.utils.time_parser.datetime")
    def test_hours(self, mock_dt):
        now = datetime(2026, 2, 13, 10, 0, 0)
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)

        result = parse_time("2시간")
        assert result == now + timedelta(hours=2)

    @patch("src.utils.time_parser.datetime")
    def test_hours_with_suffix(self, mock_dt):
        now = datetime(2026, 2, 13, 10, 0, 0)
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)

        result = parse_time("1시간 후")
        assert result == now + timedelta(hours=1)

    @patch("src.utils.time_parser.datetime")
    def test_hours_and_minutes(self, mock_dt):
        now = datetime(2026, 2, 13, 10, 0, 0)
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)

        result = parse_time("1시간 30분")
        assert result == now + timedelta(hours=1, minutes=30)

    @patch("src.utils.time_parser.datetime")
    def test_days(self, mock_dt):
        now = datetime(2026, 2, 13, 10, 0, 0)
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)

        result = parse_time("3일")
        assert result == now + timedelta(days=3)

    @patch("src.utils.time_parser.datetime")
    def test_days_with_suffix(self, mock_dt):
        now = datetime(2026, 2, 13, 10, 0, 0)
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)

        result = parse_time("1일 후")
        assert result == now + timedelta(days=1)


# ─── parse_time: 절대 시간 ───

class TestParseTimeAbsolute:
    """절대 시간 표현 파싱 테스트"""

    @patch("src.utils.time_parser.datetime")
    def test_colon_format_future(self, mock_dt):
        """14:00 형식 - 미래 시간"""
        now = datetime(2026, 2, 13, 10, 0, 0)
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)

        result = parse_time("14:00")
        assert result == datetime(2026, 2, 13, 14, 0, 0)

    @patch("src.utils.time_parser.datetime")
    def test_colon_format_past_wraps_to_next_day(self, mock_dt):
        """과거 시간이면 다음 날로"""
        now = datetime(2026, 2, 13, 15, 0, 0)
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)

        result = parse_time("14:00")
        assert result == datetime(2026, 2, 14, 14, 0, 0)

    @patch("src.utils.time_parser.datetime")
    def test_korean_hour_only(self, mock_dt):
        """14시 형식"""
        now = datetime(2026, 2, 13, 10, 0, 0)
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)

        result = parse_time("14시")
        assert result == datetime(2026, 2, 13, 14, 0, 0)

    @patch("src.utils.time_parser.datetime")
    def test_korean_hour_minute(self, mock_dt):
        """14시 30분 형식"""
        now = datetime(2026, 2, 13, 10, 0, 0)
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)

        result = parse_time("14시 30분")
        assert result == datetime(2026, 2, 13, 14, 30, 0)

    @patch("src.utils.time_parser.datetime")
    def test_am_pm_afternoon(self, mock_dt):
        """오후 2시 -> 14시"""
        now = datetime(2026, 2, 13, 10, 0, 0)
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)

        result = parse_time("오후 2시")
        assert result == datetime(2026, 2, 13, 14, 0, 0)

    @patch("src.utils.time_parser.datetime")
    def test_am_pm_morning(self, mock_dt):
        """오전 9시"""
        now = datetime(2026, 2, 13, 8, 0, 0)
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)

        result = parse_time("오전 9시")
        assert result == datetime(2026, 2, 13, 9, 0, 0)

    @patch("src.utils.time_parser.datetime")
    def test_am_12_is_midnight(self, mock_dt):
        """오전 12시 = 0시 (자정)"""
        now = datetime(2026, 2, 13, 10, 0, 0)
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)

        result = parse_time("오전 12시")
        # 오전 12시 = 0시, 현재 10시이므로 다음 날 0시
        assert result == datetime(2026, 2, 14, 0, 0, 0)

    @patch("src.utils.time_parser.datetime")
    def test_pm_12_is_noon(self, mock_dt):
        """오후 12시 = 12시 (정오)"""
        now = datetime(2026, 2, 13, 10, 0, 0)
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)

        result = parse_time("오후 12시")
        assert result == datetime(2026, 2, 13, 12, 0, 0)

    @patch("src.utils.time_parser.datetime")
    def test_pm_with_minutes(self, mock_dt):
        """오후 2시 30분"""
        now = datetime(2026, 2, 13, 10, 0, 0)
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)

        result = parse_time("오후 2시 30분")
        assert result == datetime(2026, 2, 13, 14, 30, 0)


# ─── parse_time: 엣지 케이스 ───

class TestParseTimeEdgeCases:
    """파싱 실패 및 엣지 케이스"""

    def test_invalid_string_returns_none(self):
        assert parse_time("내일 아침") is None

    def test_empty_string_returns_none(self):
        assert parse_time("") is None

    def test_whitespace_only_returns_none(self):
        assert parse_time("   ") is None

    def test_random_text_returns_none(self):
        assert parse_time("hello world") is None


# ─── format_datetime ───

class TestFormatDatetime:
    def test_with_datetime_object(self):
        dt = datetime(2026, 2, 13, 14, 30, 0)
        assert format_datetime(dt) == "02/13 14:30"

    def test_with_iso_string(self):
        assert format_datetime("2026-02-13T14:30:00") == "02/13 14:30"

    def test_with_midnight(self):
        dt = datetime(2026, 1, 1, 0, 0, 0)
        assert format_datetime(dt) == "01/01 00:00"


# ─── validate_time_format ───

class TestValidateTimeFormat:
    """validate_time_format() 공용 헬퍼 함수 테스트 (IMP-017 구현)"""

    def test_valid_0800(self):
        is_valid, err = validate_time_format("08:00")
        assert is_valid is True
        assert err is None

    def test_valid_0000(self):
        is_valid, err = validate_time_format("00:00")
        assert is_valid is True

    def test_valid_2359(self):
        is_valid, err = validate_time_format("23:59")
        assert is_valid is True

    def test_valid_1230(self):
        is_valid, err = validate_time_format("12:30")
        assert is_valid is True

    def test_invalid_no_colon(self):
        is_valid, err = validate_time_format("0800")
        assert is_valid is False
        assert err is not None

    def test_invalid_hour_24(self):
        is_valid, err = validate_time_format("24:00")
        assert is_valid is False
        assert "올바르지 않습니다" in err

    def test_invalid_hour_25(self):
        is_valid, err = validate_time_format("25:00")
        assert is_valid is False

    def test_invalid_minute_60(self):
        is_valid, err = validate_time_format("12:60")
        assert is_valid is False

    def test_invalid_minute_99(self):
        is_valid, err = validate_time_format("12:99")
        assert is_valid is False

    def test_invalid_non_numeric(self):
        is_valid, err = validate_time_format("ab:cd")
        assert is_valid is False
        assert "형식" in err

    def test_invalid_korean(self):
        is_valid, err = validate_time_format("오전:칠시")
        assert is_valid is False

    def test_invalid_empty_string(self):
        is_valid, err = validate_time_format("")
        assert is_valid is False

    def test_invalid_too_many_colons(self):
        is_valid, err = validate_time_format("12:30:00")
        assert is_valid is False

    def test_negative_hour(self):
        is_valid, err = validate_time_format("-1:00")
        assert is_valid is False

    def test_returns_tuple(self):
        """반환 타입이 항상 (bool, str|None) 튜플"""
        result = validate_time_format("08:00")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
