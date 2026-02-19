from discord import Message

from src.bot.tools import ToolContext, ToolRegistry
from src.bot.tools.briefing import BriefingTool
from src.bot.tools.exchange import ExchangeTool
from src.bot.tools.memo import MemoTool
from src.bot.tools.persona import PersonaTool
from src.bot.tools.reminder import ReminderTool
from src.bot.tools.search import SearchTool
from src.bot.tools.weather import WeatherTool
from src.db import DB
from src.llm.ollama_client import OllamaClient
from src.utils.logger import setup_logger
from src.utils.web import extract_urls, get_page_content

logger = setup_logger(__name__)

MAX_TOOL_ROUNDS = 3


class ChatHandler:
    """Handler for normal chat messages."""

    def __init__(self, db: DB, ollama: OllamaClient):
        self.db = db
        self.ollama = ollama

        self.registry = ToolRegistry()
        self.registry.register(WeatherTool())
        self.registry.register(ExchangeTool())
        self.registry.register(ReminderTool())
        self.registry.register(PersonaTool())
        self.registry.register(MemoTool())
        self.registry.register(SearchTool())
        self.registry.register(BriefingTool())

    async def handle(self, message: Message, user_id: str, user_content: str, persona: dict):
        """Handle normal chat with persona."""
        async with message.channel.typing():
            # Check for URLs and fetch content
            urls = extract_urls(user_content)
            url_contents = []

            for url in urls[:3]:
                content = await get_page_content(url)
                if content:
                    if len(content) > 4000:
                        content = content[:4000] + "...(truncated)"
                    url_contents.append(f"[Content from {url}]\n{content}")

            if url_contents:
                context = "\n\n".join(url_contents)
                enhanced_content = f"{user_content}\n\n---\n{context}"
            else:
                enhanced_content = user_content

            summary = await self.db.conversation.get_summary(user_id)
            history = await self.db.conversation.get_history(user_id)
            history.append({"role": "user", "content": enhanced_content})

            try:
                response = await self._chat_with_tools(history, persona, user_id, summary=summary)

                await self.db.conversation.add_message(user_id, "user", user_content)
                await self.db.conversation.add_message(user_id, "assistant", response)

                await self._send_response(message, response)
                await self._maybe_compress(user_id, persona)

            except Exception as e:
                logger.error(f"Chat handler error: {str(e)}", exc_info=True)
                await message.reply(f"오류가 발생했습니다: {str(e)}")

    async def _chat_with_tools(self, history: list[dict], persona: dict, user_id: str, summary: str | None = None) -> str:
        """Chat with LLM, detecting and executing tool calls in a loop."""
        context = ToolContext(user_id=user_id, db=self.db, persona=persona)
        tool_instructions = self.registry.build_tool_instructions()

        for _ in range(MAX_TOOL_ROUNDS):
            response = await self.ollama.chat(
                history, persona=persona, summary=summary,
                tool_instructions=tool_instructions
            )

            tool_result = None
            for tool in self.registry.tools:
                tool_result = await tool.try_execute(response, context)
                if tool_result is not None:
                    break

            if tool_result is None:
                return response

            history.append({"role": "assistant", "content": response})
            history.append({"role": "user", "content": f"[Tool Result]\n{tool_result}\n\nBased on this data, answer the user's original question naturally."})

        return response

    async def _maybe_compress(self, user_id: str, persona: dict):
        """Compress old messages into a summary if message count exceeds threshold."""
        from src.config import SUMMARY_THRESHOLD, SUMMARY_KEEP_RECENT

        count = await self.db.conversation.get_message_count(user_id)
        if count <= SUMMARY_THRESHOLD:
            return

        all_messages = await self.db.conversation.get_all_messages(user_id)
        to_summarize = all_messages[:-SUMMARY_KEEP_RECENT]
        if not to_summarize:
            return

        existing_summary = await self.db.conversation.get_summary(user_id)

        conversation_text = "\n".join(
            f"[{m['role'].upper()}]: {m['content']}" for m in to_summarize
        )

        if existing_summary:
            prompt = f"""다음은 사용자와 AI 어시스턴트의 이전 대화입니다. 핵심 정보를 간결하게 요약해주세요.

유지해야 할 정보:
- 사용자의 이름, 선호도, 습관 등 개인 정보
- 진행 중인 작업이나 프로젝트
- 주요 결정사항이나 약속
- 대화의 전반적인 톤과 관계

기존 요약:
{existing_summary}

추가 대화:
{conversation_text}

위 내용을 3-5문장의 한국어로 요약해주세요. 불필요한 인사말이나 잡담은 제외하고 핵심 정보만 남겨주세요."""
        else:
            prompt = f"""다음은 사용자와 AI 어시스턴트의 이전 대화입니다. 핵심 정보를 간결하게 요약해주세요.

유지해야 할 정보:
- 사용자의 이름, 선호도, 습관 등 개인 정보
- 진행 중인 작업이나 프로젝트
- 주요 결정사항이나 약속
- 대화의 전반적인 톤과 관계

{conversation_text}

위 내용을 3-5문장의 한국어로 요약해주세요. 불필요한 인사말이나 잡담은 제외하고 핵심 정보만 남겨주세요."""

        try:
            new_summary = await self.ollama.chat(
                [{"role": "user", "content": prompt}],
                persona=None
            )
            await self.db.conversation.save_summary(user_id, new_summary, len(to_summarize))
            await self.db.conversation.delete_old_messages(user_id, SUMMARY_KEEP_RECENT)
            logger.info(f"Compressed {len(to_summarize)} messages into summary for user {user_id}")
        except Exception as e:
            logger.warning(f"Summary compression failed for user {user_id}: {e}")

    async def _send_response(self, message: Message, response: str):
        """Send response, splitting if necessary."""
        if len(response) > 2000:
            chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
            for chunk in chunks:
                await message.reply(chunk)
        else:
            await message.reply(response)
