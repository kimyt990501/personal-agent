"""Tests for ToolRegistry - registration, instruction synthesis, and iteration."""
import pytest

from src.bot.tools import ToolRegistry
from src.bot.tools.briefing import BriefingTool
from src.bot.tools.exchange import ExchangeTool
from src.bot.tools.filesystem import FileSystemTool
from src.bot.tools.memo import MemoTool
from src.bot.tools.persona import PersonaTool
from src.bot.tools.reminder import ReminderTool
from src.bot.tools.search import SearchTool
from src.bot.tools.weather import WeatherTool


# ─── Registration ───

class TestToolRegistryRegistration:
    def test_register_single_tool(self):
        registry = ToolRegistry()
        registry.register(WeatherTool())
        assert len(registry.tools) == 1

    def test_register_multiple_tools(self):
        registry = ToolRegistry()
        registry.register(WeatherTool())
        registry.register(ExchangeTool())
        registry.register(MemoTool())
        assert len(registry.tools) == 3

    def test_tools_property_returns_copy(self):
        """tools 프로퍼티는 내부 리스트의 복사본을 반환해야 함"""
        registry = ToolRegistry()
        registry.register(WeatherTool())
        tools1 = registry.tools
        tools2 = registry.tools
        assert tools1 is not tools2  # 별도 복사본

    def test_empty_registry(self):
        registry = ToolRegistry()
        assert registry.tools == []

    def test_all_seven_tools(self):
        """7개 도구 모두 등록 가능"""
        registry = ToolRegistry()
        for tool_cls in [WeatherTool, ExchangeTool, ReminderTool, PersonaTool, MemoTool, SearchTool, BriefingTool]:
            registry.register(tool_cls())
        assert len(registry.tools) == 7

    def test_all_eight_tools_with_filesystem(self):
        """FileSystemTool 포함 8개 도구 모두 등록 가능"""
        registry = ToolRegistry()
        for tool_cls in [WeatherTool, ExchangeTool, ReminderTool, PersonaTool, MemoTool, SearchTool, BriefingTool, FileSystemTool]:
            registry.register(tool_cls())
        assert len(registry.tools) == 8


# ─── build_tool_instructions ───

class TestToolRegistryBuildInstructions:
    def test_weather_tag_in_instructions(self):
        registry = ToolRegistry()
        registry.register(WeatherTool())
        instructions = registry.build_tool_instructions()
        assert "[WEATHER:" in instructions

    def test_exchange_tag_in_instructions(self):
        registry = ToolRegistry()
        registry.register(ExchangeTool())
        instructions = registry.build_tool_instructions()
        assert "[EXCHANGE:" in instructions

    def test_memo_tags_in_instructions(self):
        registry = ToolRegistry()
        registry.register(MemoTool())
        instructions = registry.build_tool_instructions()
        assert "[MEMO_SAVE:" in instructions
        assert "[MEMO_LIST]" in instructions
        assert "[MEMO_SEARCH:" in instructions
        assert "[MEMO_DEL:" in instructions

    def test_briefing_tags_in_instructions(self):
        registry = ToolRegistry()
        registry.register(BriefingTool())
        instructions = registry.build_tool_instructions()
        assert "[BRIEFING_SET:" in instructions
        assert "[BRIEFING_GET]" in instructions

    def test_reminder_tag_in_instructions(self):
        registry = ToolRegistry()
        registry.register(ReminderTool())
        instructions = registry.build_tool_instructions()
        assert "[REMINDER:" in instructions

    def test_persona_tag_in_instructions(self):
        registry = ToolRegistry()
        registry.register(PersonaTool())
        instructions = registry.build_tool_instructions()
        assert "[PERSONA:" in instructions

    def test_search_tag_in_instructions(self):
        registry = ToolRegistry()
        registry.register(SearchTool())
        instructions = registry.build_tool_instructions()
        assert "[SEARCH:" in instructions

    def test_all_tools_instructions_combined(self):
        """7개 도구 모두 등록 시 모든 태그가 포함되어야 함"""
        registry = ToolRegistry()
        for tool_cls in [WeatherTool, ExchangeTool, ReminderTool, PersonaTool, MemoTool, SearchTool, BriefingTool]:
            registry.register(tool_cls())
        instructions = registry.build_tool_instructions()

        assert "[WEATHER:" in instructions
        assert "[EXCHANGE:" in instructions
        assert "[REMINDER:" in instructions
        assert "[PERSONA:" in instructions
        assert "[MEMO_SAVE:" in instructions
        assert "[SEARCH:" in instructions
        assert "[BRIEFING_SET:" in instructions

    def test_filesystem_tags_in_instructions(self):
        """FileSystemTool 등록 시 FS 태그가 포함되어야 함"""
        registry = ToolRegistry()
        registry.register(FileSystemTool())
        instructions = registry.build_tool_instructions()
        assert "FS_LS" in instructions
        assert "FS_READ" in instructions
        assert "FS_FIND" in instructions
        assert "FS_INFO" in instructions

    def test_empty_registry_instructions_has_structure(self):
        """빈 레지스트리도 구조화된 문자열 반환"""
        registry = ToolRegistry()
        instructions = registry.build_tool_instructions()
        assert "Available tools:" in instructions

    def test_translation_rule_always_included(self):
        """번역 규칙은 레지스트리 자체에서 항상 포함"""
        registry = ToolRegistry()
        instructions = registry.build_tool_instructions()
        assert "번역" in instructions or "translat" in instructions.lower()

    def test_usage_rules_section_present(self):
        registry = ToolRegistry()
        registry.register(WeatherTool())
        instructions = registry.build_tool_instructions()
        assert "Rules:" in instructions

    def test_descriptions_combined_from_all_tools(self):
        """각 도구의 description이 합쳐져서 포함됨"""
        registry = ToolRegistry()
        registry.register(WeatherTool())
        registry.register(SearchTool())
        instructions = registry.build_tool_instructions()
        assert "Weather" in instructions
        assert "Search" in instructions


# ─── Iteration and ordering ───

class TestToolRegistryIteration:
    def test_tools_iterable(self):
        registry = ToolRegistry()
        registry.register(WeatherTool())
        registry.register(ExchangeTool())
        names = [tool.name for tool in registry.tools]
        assert "weather" in names
        assert "exchange" in names

    def test_tools_order_preserved(self):
        """등록 순서가 보존되어야 함 (도구 실행 순서 결정론적)"""
        registry = ToolRegistry()
        registry.register(WeatherTool())
        registry.register(MemoTool())
        registry.register(SearchTool())
        names = [tool.name for tool in registry.tools]
        assert names.index("weather") < names.index("memo")
        assert names.index("memo") < names.index("search")

    def test_tool_names_are_unique(self):
        """각 도구의 name이 고유한지 확인"""
        registry = ToolRegistry()
        for tool_cls in [WeatherTool, ExchangeTool, ReminderTool, PersonaTool, MemoTool, SearchTool, BriefingTool, FileSystemTool]:
            registry.register(tool_cls())
        names = [tool.name for tool in registry.tools]
        assert len(names) == len(set(names))


# ─── Tool ABC compliance ───

class TestToolAbcCompliance:
    """각 Tool 클래스가 ABC 계약을 올바르게 구현하는지 확인"""

    @pytest.mark.parametrize("tool_cls", [
        WeatherTool, ExchangeTool, ReminderTool,
        PersonaTool, MemoTool, SearchTool, BriefingTool, FileSystemTool,
    ])
    def test_name_property_is_string(self, tool_cls):
        tool = tool_cls()
        assert isinstance(tool.name, str)
        assert len(tool.name) > 0

    @pytest.mark.parametrize("tool_cls", [
        WeatherTool, ExchangeTool, ReminderTool,
        PersonaTool, MemoTool, SearchTool, BriefingTool, FileSystemTool,
    ])
    def test_description_property_is_string(self, tool_cls):
        tool = tool_cls()
        assert isinstance(tool.description, str)
        assert len(tool.description) > 0

    @pytest.mark.parametrize("tool_cls", [
        WeatherTool, ExchangeTool, ReminderTool,
        PersonaTool, MemoTool, SearchTool, BriefingTool, FileSystemTool,
    ])
    def test_usage_rules_property_is_string(self, tool_cls):
        tool = tool_cls()
        assert isinstance(tool.usage_rules, str)  # may be empty string
