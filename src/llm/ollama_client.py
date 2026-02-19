import ollama
from ollama import AsyncClient

from src.config import OLLAMA_HOST, OLLAMA_MODEL
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class OllamaClient:
    def __init__(self, host: str = OLLAMA_HOST, model: str = OLLAMA_MODEL):
        self.client = AsyncClient(host=host)
        self.model = model

    def build_system_prompt(self, persona: dict | None = None, summary: str | None = None, tool_instructions: str | None = None) -> str:
        """Build system prompt with optional persona, conversation summary, and tool instructions."""
        tool_section = tool_instructions or ""

        summary_section = ""
        if summary:
            summary_section = f"""

[이전 대화 요약]
{summary}
위 요약은 이전 대화의 핵심 내용입니다. 이 맥락을 참고하여 자연스럽게 대화를 이어가세요."""

        if persona:
            return f"""You are {persona['name']}, a personal AI assistant.
Your role: {persona['role']}
Your tone/style: {persona['tone']}

You are running locally on the user's Mac Mini via Ollama ({self.model}).
Always stay in character. Answer in the same language the user uses.
Never claim to be Claude, ChatGPT, or any other AI.
{tool_section}{summary_section}"""
        else:
            return f"""You are a personal AI assistant powered by {self.model}.
You are running locally on the user's Mac Mini via Ollama.
Be concise, helpful, and friendly. Answer in the same language the user uses.
Never claim to be Claude, ChatGPT, or any other AI.
{tool_section}{summary_section}"""

    async def chat(self, messages: list[dict], persona: dict | None = None, summary: str | None = None, tool_instructions: str | None = None) -> str:
        """Send messages to Ollama and get a response."""
        system_prompt = self.build_system_prompt(persona, summary=summary, tool_instructions=tool_instructions)

        full_messages = [
            {"role": "system", "content": system_prompt},
            *messages
        ]

        response = await self.client.chat(
            model=self.model,
            messages=full_messages,
        )

        return response["message"]["content"]

    async def check_health(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            response = await self.client.list()
            model_names = [m.model for m in response.models]
            return any(self.model in name for name in model_names)
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False
