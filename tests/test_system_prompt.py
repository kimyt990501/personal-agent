"""Tests for OllamaClient.build_system_prompt() - verifying tool instructions"""
import pytest

from src.llm.ollama_client import OllamaClient


@pytest.fixture
def client():
    return OllamaClient()


class TestSystemPromptToolInstructions:
    """시스템 프롬프트에 모든 도구 안내가 포함되는지 확인"""

    def test_contains_weather_instructions(self, client):
        prompt = client.build_system_prompt()
        assert "[WEATHER:" in prompt

    def test_contains_exchange_instructions(self, client):
        prompt = client.build_system_prompt()
        assert "[EXCHANGE:" in prompt

    def test_contains_reminder_instructions(self, client):
        prompt = client.build_system_prompt()
        assert "[REMINDER:" in prompt

    def test_contains_persona_instructions(self, client):
        prompt = client.build_system_prompt()
        assert "[PERSONA:" in prompt

    def test_contains_memo_save_instructions(self, client):
        prompt = client.build_system_prompt()
        assert "[MEMO_SAVE:" in prompt

    def test_contains_memo_list_instructions(self, client):
        prompt = client.build_system_prompt()
        assert "[MEMO_LIST]" in prompt

    def test_contains_memo_search_instructions(self, client):
        prompt = client.build_system_prompt()
        assert "[MEMO_SEARCH:" in prompt

    def test_contains_memo_del_instructions(self, client):
        prompt = client.build_system_prompt()
        assert "[MEMO_DEL:" in prompt

    def test_contains_search_instructions(self, client):
        prompt = client.build_system_prompt()
        assert "[SEARCH:" in prompt

    def test_contains_memo_usage_rules(self, client):
        """메모 사용 규칙이 포함되는지"""
        prompt = client.build_system_prompt()
        assert "메모해줘" in prompt or "memo" in prompt.lower()

    def test_contains_search_usage_rules(self, client):
        """검색 사용 규칙이 포함되는지"""
        prompt = client.build_system_prompt()
        assert "검색" in prompt or "search" in prompt.lower()

    def test_contains_translation_rule(self, client):
        """번역 관련 규칙이 포함되는지 (번역은 도구 태그 없이 직접)"""
        prompt = client.build_system_prompt()
        assert "번역" in prompt or "translat" in prompt.lower()


class TestSystemPromptWithPersona:
    def test_persona_included(self, client):
        persona = {"name": "뽀삐", "role": "개인 비서", "tone": "친근한 반말"}
        prompt = client.build_system_prompt(persona)
        assert "뽀삐" in prompt
        assert "개인 비서" in prompt
        assert "친근한 반말" in prompt

    def test_persona_includes_tool_instructions(self, client):
        """페르소나가 있어도 도구 안내는 포함되어야 함"""
        persona = {"name": "뽀삐", "role": "비서", "tone": "반말"}
        prompt = client.build_system_prompt(persona)
        assert "[MEMO_SAVE:" in prompt
        assert "[SEARCH:" in prompt

    def test_no_persona(self, client):
        prompt = client.build_system_prompt(None)
        assert "personal AI assistant" in prompt
