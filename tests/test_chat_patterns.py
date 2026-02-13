"""Tests for tool call regex patterns in src/bot/handlers/chat.py"""
import re
import pytest

from src.bot.handlers.chat import (
    WEATHER_PATTERN,
    EXCHANGE_PATTERN,
    REMINDER_PATTERN,
    PERSONA_PATTERN,
)


# ─── WEATHER_PATTERN ───

class TestWeatherPattern:
    def test_basic_city(self):
        match = WEATHER_PATTERN.search("[WEATHER:서울]")
        assert match is not None
        assert match.group(1) == "서울"

    def test_english_city(self):
        match = WEATHER_PATTERN.search("[WEATHER:Tokyo]")
        assert match is not None
        assert match.group(1) == "Tokyo"

    def test_embedded_in_text(self):
        text = "날씨를 확인하겠습니다. [WEATHER:부산] 잠시만 기다려주세요."
        match = WEATHER_PATTERN.search(text)
        assert match is not None
        assert match.group(1) == "부산"

    def test_no_match(self):
        assert WEATHER_PATTERN.search("날씨가 좋네요") is None

    def test_empty_city(self):
        """빈 도시명은 매칭하지 않아야 함"""
        match = WEATHER_PATTERN.search("[WEATHER:]")
        assert match is None


# ─── EXCHANGE_PATTERN ───

class TestExchangePattern:
    def test_basic(self):
        match = EXCHANGE_PATTERN.search("[EXCHANGE:100,USD,KRW]")
        assert match is not None
        assert match.group(1) == "100"
        assert match.group(2) == "USD"
        assert match.group(3) == "KRW"

    def test_decimal_amount(self):
        match = EXCHANGE_PATTERN.search("[EXCHANGE:50.5,EUR,USD]")
        assert match is not None
        assert match.group(1) == "50.5"

    def test_embedded_in_text(self):
        text = "환율을 확인할게요. [EXCHANGE:1000,JPY,KRW]"
        match = EXCHANGE_PATTERN.search(text)
        assert match is not None
        assert match.group(2) == "JPY"

    def test_no_match(self):
        assert EXCHANGE_PATTERN.search("100달러를 원화로") is None


# ─── REMINDER_PATTERN ───

class TestReminderPattern:
    def test_basic(self):
        match = REMINDER_PATTERN.search("[REMINDER:30분,회의 참석]")
        assert match is not None
        assert match.group(1) == "30분"
        assert match.group(2) == "회의 참석"

    def test_content_with_special_chars(self):
        match = REMINDER_PATTERN.search("[REMINDER:1시간,약 먹기! 중요함]")
        assert match is not None
        assert "약 먹기" in match.group(2)

    def test_embedded_in_text(self):
        text = "알겠습니다! [REMINDER:14:00,점심 약속] 등록했어요."
        match = REMINDER_PATTERN.search(text)
        assert match is not None
        assert match.group(1) == "14:00"

    def test_no_match(self):
        assert REMINDER_PATTERN.search("30분 후에 알려줘") is None


# ─── PERSONA_PATTERN ───

class TestPersonaPattern:
    def test_basic(self):
        match = PERSONA_PATTERN.search("[PERSONA:뽀삐,개인 비서,친근한 반말]")
        assert match is not None
        assert match.group(1) == "뽀삐"
        assert match.group(2) == "개인 비서"
        assert match.group(3) == "친근한 반말"

    def test_embedded_in_text(self):
        text = "페르소나를 변경합니다. [PERSONA:쿠키,친구,존댓말]"
        match = PERSONA_PATTERN.search(text)
        assert match is not None

    def test_no_match(self):
        assert PERSONA_PATTERN.search("이름을 바꿔줘") is None


# ─── 복합 패턴 감지 테스트 ───

class TestMultiplePatterns:
    def test_weather_and_reminder_in_same_text(self):
        text = "[WEATHER:서울] 확인 후 [REMINDER:30분,우산 챙기기]"
        assert WEATHER_PATTERN.search(text) is not None
        assert REMINDER_PATTERN.search(text) is not None

    def test_all_patterns_findall(self):
        """findall로 여러 매치 추출 가능"""
        text = "먼저 [WEATHER:서울] 보고, [WEATHER:부산]도 확인해줘"
        matches = WEATHER_PATTERN.findall(text)
        assert len(matches) == 2
        assert matches[0] == "서울"
        assert matches[1] == "부산"
