import re

from src.bot.tools.base import Tool, ToolContext
from src.utils.logger import setup_logger
from src.utils.web import web_search, format_search_results

logger = setup_logger(__name__)


class SearchTool(Tool):
    PATTERN = re.compile(r"\[SEARCH:(.+)\]")

    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return (
            "- Search: When the user asks about recent events, current information, or anything requiring up-to-date data beyond your knowledge, output [SEARCH:query]\n"
            "  - e.g. [SEARCH:비트코인 시세], [SEARCH:파이썬 3.13 새 기능], [SEARCH:2026 아이폰 출시일]\n"
            "  - Use only when your knowledge is insufficient or the user explicitly asks you to search the web"
        )

    @property
    def usage_rules(self) -> str:
        return (
            "- For search, use when the question requires current/recent information or the user explicitly asks to search. "
            "Extract the core search query from their question."
        )

    async def try_execute(self, response: str, context: ToolContext) -> str | None:
        match = self.PATTERN.search(response)
        if not match:
            return None

        query = match.group(1).strip()
        logger.info(f"Tool called: [SEARCH:{query}]")
        results = await web_search(query)

        if not results:
            return f"'{query}' 검색 결과를 가져오지 못했습니다."

        search_context = format_search_results(results)
        return f"검색 결과 ('{query}'):\n{search_context}"
