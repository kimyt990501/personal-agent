from discord import Message

from src.db import DB
from src.llm.ollama_client import OllamaClient
from src.utils.web import web_search, format_search_results


class SearchHandler:
    """Handler for web search commands."""

    def __init__(self, db: DB, ollama: OllamaClient):
        self.db = db
        self.ollama = ollama

    async def handle(self, message: Message, user_id: str, query: str, persona: dict | None):
        """Handle web search and respond with AI analysis."""
        if not query:
            await message.reply("검색어를 입력해주세요. 예: `/s 오늘 날씨`")
            return

        async with message.channel.typing():
            # Perform web search
            results = await web_search(query)

            if not results:
                await message.reply("검색 결과를 가져오지 못했어요. 다시 시도해주세요.")
                return

            # Format search results
            search_context = format_search_results(results)

            # Build prompt with search results
            search_prompt = (
                f"사용자가 '{query}'에 대해 검색했습니다.\n\n"
                f"**검색 결과:**\n{search_context}\n\n"
                f"위 검색 결과를 바탕으로 사용자의 질문에 답변해주세요."
            )

            history = await self.db.conversation.get_history(user_id)
            history.append({"role": "user", "content": search_prompt})

            try:
                response = await self.ollama.chat(history, persona=persona)

                # Save to memory
                await self.db.conversation.add_message(user_id, "user", f"[검색: {query}]")
                await self.db.conversation.add_message(user_id, "assistant", response)

                await self._send_response(message, response)

            except Exception as e:
                await message.reply(f"오류가 발생했습니다: {str(e)}")

    async def _send_response(self, message: Message, response: str):
        """Send response, splitting if necessary."""
        if len(response) > 2000:
            chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
            for chunk in chunks:
                await message.reply(chunk)
        else:
            await message.reply(response)
