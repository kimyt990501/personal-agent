"""Tests for src/utils/time_parser.py"""
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from src.utils.time_parser import parse_time, format_datetime


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
