"""Tests for OllamaClient.build_system_prompt() - verifying tool instructions"""
import pytest

from src.bot.tools import ToolRegistry
from src.bot.tools.briefing import BriefingTool
from src.bot.tools.exchange import ExchangeTool
from src.bot.tools.memo import MemoTool
from src.bot.tools.persona import PersonaTool
from src.bot.tools.reminder import ReminderTool
from src.bot.tools.search import SearchTool
from src.bot.tools.weather import WeatherTool
from src.llm.ollama_client import OllamaClient


@pytest.fixture
def client():
    return OllamaClient()


@pytest.fixture
def tool_instructions():
    """Build tool instructions from the full registry (all 7 tools)."""
    registry = ToolRegistry()
    registry.register(WeatherTool())
    registry.register(ExchangeTool())
    registry.register(ReminderTool())
    registry.register(PersonaTool())
    registry.register(MemoTool())
    registry.register(SearchTool())
    registry.register(BriefingTool())
    return registry.build_tool_instructions()


class TestSystemPromptToolInstructions:
    """시스템 프롬프트에 모든 도구 안내가 포함되는지 확인"""

    def test_contains_weather_instructions(self, client, tool_instructions):
        prompt = client.build_system_prompt(tool_instructions=tool_instructions)
        assert "[WEATHER:" in prompt

    def test_contains_exchange_instructions(self, client, tool_instructions):
        prompt = client.build_system_prompt(tool_instructions=tool_instructions)
        assert "[EXCHANGE:" in prompt

    def test_contains_reminder_instructions(self, client, tool_instructions):
        prompt = client.build_system_prompt(tool_instructions=tool_instructions)
        assert "[REMINDER:" in prompt

    def test_contains_persona_instructions(self, client, tool_instructions):
        prompt = client.build_system_prompt(tool_instructions=tool_instructions)
        assert "[PERSONA:" in prompt

    def test_contains_memo_save_instructions(self, client, tool_instructions):
        prompt = client.build_system_prompt(tool_instructions=tool_instructions)
        assert "[MEMO_SAVE:" in prompt

    def test_contains_memo_list_instructions(self, client, tool_instructions):
        prompt = client.build_system_prompt(tool_instructions=tool_instructions)
        assert "[MEMO_LIST]" in prompt

    def test_contains_memo_search_instructions(self, client, tool_instructions):
        prompt = client.build_system_prompt(tool_instructions=tool_instructions)
        assert "[MEMO_SEARCH:" in prompt

    def test_contains_memo_del_instructions(self, client, tool_instructions):
        prompt = client.build_system_prompt(tool_instructions=tool_instructions)
        assert "[MEMO_DEL:" in prompt

    def test_contains_search_instructions(self, client, tool_instructions):
        prompt = client.build_system_prompt(tool_instructions=tool_instructions)
        assert "[SEARCH:" in prompt

    def test_contains_memo_usage_rules(self, client, tool_instructions):
        """메모 사용 규칙이 포함되는지"""
        prompt = client.build_system_prompt(tool_instructions=tool_instructions)
        assert "메모해줘" in prompt or "memo" in prompt.lower()

    def test_contains_search_usage_rules(self, client, tool_instructions):
        """검색 사용 규칙이 포함되는지"""
        prompt = client.build_system_prompt(tool_instructions=tool_instructions)
        assert "검색" in prompt or "search" in prompt.lower()

    def test_contains_translation_rule(self, client, tool_instructions):
        """번역 관련 규칙이 포함되는지 (번역은 도구 태그 없이 직접)"""
        prompt = client.build_system_prompt(tool_instructions=tool_instructions)
        assert "번역" in prompt or "translat" in prompt.lower()

    def test_memo_del_uses_position_not_id(self, client, tool_instructions):
        """MEMO_DEL 안내가 position 기반으로 변경되었는지"""
        prompt = client.build_system_prompt(tool_instructions=tool_instructions)
        assert "position" in prompt.lower()


class TestSystemPromptWithPersona:
    def test_persona_included(self, client):
        persona = {"name": "뽀삐", "role": "개인 비서", "tone": "친근한 반말"}
        prompt = client.build_system_prompt(persona)
        assert "뽀삐" in prompt
        assert "개인 비서" in prompt
        assert "친근한 반말" in prompt

    def test_persona_includes_tool_instructions(self, client, tool_instructions):
        """페르소나가 있어도 도구 안내는 포함되어야 함"""
        persona = {"name": "뽀삐", "role": "비서", "tone": "반말"}
        prompt = client.build_system_prompt(persona, tool_instructions=tool_instructions)
        assert "[MEMO_SAVE:" in prompt
        assert "[SEARCH:" in prompt

    def test_no_persona(self, client):
        prompt = client.build_system_prompt(None)
        assert "personal AI assistant" in prompt


class TestSystemPromptBriefingInstructions:
    """시스템 프롬프트에 브리핑 도구 안내가 포함되는지 확인"""

    def test_contains_briefing_set_tag(self, client, tool_instructions):
        prompt = client.build_system_prompt(tool_instructions=tool_instructions)
        assert "[BRIEFING_SET:" in prompt

    def test_contains_briefing_get_tag(self, client, tool_instructions):
        prompt = client.build_system_prompt(tool_instructions=tool_instructions)
        assert "[BRIEFING_GET]" in prompt

    def test_contains_briefing_usage_rules(self, client, tool_instructions):
        """브리핑 사용 규칙이 포함되는지"""
        prompt = client.build_system_prompt(tool_instructions=tool_instructions)
        assert "브리핑" in prompt or "briefing" in prompt.lower()


class TestSystemPromptSummaryInjection:
    """대화 요약이 시스템 프롬프트에 올바르게 주입되는지 확인"""

    def test_summary_injected_when_provided(self, client):
        summary = "사용자 이름은 김철수이고 파이썬 프로젝트를 진행 중이다."
        prompt = client.build_system_prompt(summary=summary)
        assert "[이전 대화 요약]" in prompt
        assert summary in prompt

    def test_no_summary_section_when_none(self, client):
        prompt = client.build_system_prompt(summary=None)
        assert "[이전 대화 요약]" not in prompt

    def test_summary_injected_with_persona(self, client):
        persona = {"name": "제이", "role": "비서", "tone": "존댓말"}
        summary = "사용자는 매일 아침 브리핑을 선호한다."
        prompt = client.build_system_prompt(persona=persona, summary=summary)
        assert "[이전 대화 요약]" in prompt
        assert summary in prompt
        assert "제이" in prompt

    def test_summary_context_instruction_included(self, client):
        prompt = client.build_system_prompt(summary="테스트 요약")
        assert "이 맥락을 참고하여" in prompt

    def test_empty_summary_not_injected(self, client):
        """빈 문자열 summary는 주입되지 않는다."""
        prompt = client.build_system_prompt(summary="")
        assert "[이전 대화 요약]" not in prompt
