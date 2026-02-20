from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class ToolContext:
    user_id: str
    db: Any      # DB instance — typed as Any to avoid circular import
    persona: dict  # mutable — PersonaTool modifies in-place


@dataclass
class ToolResult:
    result: str
    stop_loop: bool = False


class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool identifier (e.g. 'weather', 'memo')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Text for the 'Available tools' section of the system prompt."""
        ...

    @property
    @abstractmethod
    def usage_rules(self) -> str:
        """Text for the 'Rules' section of the system prompt.
        Return empty string if no specific rules are needed."""
        ...

    @abstractmethod
    async def try_execute(self, response: str, context: ToolContext) -> "str | ToolResult | None":
        """Match pattern in LLM response, execute, and return result.
        Returns None if pattern not found.
        Returns ToolResult with stop_loop=True to short-circuit the tool loop."""
        ...


class ToolRegistry:
    def __init__(self):
        self._tools: list[Tool] = []

    def register(self, tool: Tool):
        self._tools.append(tool)

    @property
    def tools(self) -> list[Tool]:
        return list(self._tools)

    def build_tool_instructions(self) -> str:
        """Synthesize tool descriptions and rules into a system prompt string."""
        descriptions = "\n".join(t.description for t in self._tools)
        rules = "\n".join(t.usage_rules for t in self._tools if t.usage_rules)
        return f"""
You have access to the following tools. When you need real-time information or to perform an action, use them by outputting the exact tag format.
IMPORTANT: Output ONLY the tag with no other text when you use a tool.

Available tools:
{descriptions}

Rules:
- Use tools only when the user is clearly asking for real-time information or requesting an action.
{rules}
- For translation requests ("번역해줘", "영어로", "translate this"), directly translate without using any tool tag. You have built-in multilingual capabilities.
- Output ONLY the tool tag, nothing else. Do not add any explanation before or after the tag."""
