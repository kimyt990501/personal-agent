import re

import aiohttp

from src.bot.tools.base import Tool, ToolContext
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

EXCHANGE_API_URL = "https://open.er-api.com/v6/latest/{base}"
CURRENCY_NAMES = {
    "KRW": "한국 원",
    "USD": "미국 달러",
    "JPY": "일본 엔",
    "EUR": "유로",
    "GBP": "영국 파운드",
    "CNY": "중국 위안",
}


class ExchangeTool(Tool):
    PATTERN = re.compile(r"\[EXCHANGE:(.+?),(.+?),(.+?)\]")

    @property
    def name(self) -> str:
        return "exchange"

    @property
    def description(self) -> str:
        return (
            "- Exchange: When the user asks about currency exchange rates, output [EXCHANGE:amount,FROM,TO] (e.g. [EXCHANGE:100,USD,KRW], [EXCHANGE:1,JPY,KRW])\n"
            "  - amount: the numeric amount to convert (default 1 if not specified)\n"
            "  - FROM/TO: 3-letter currency codes (e.g. USD, KRW, JPY, EUR, GBP, CNY)"
        )

    @property
    def usage_rules(self) -> str:
        return (
            "- For exchange, extract the amount and currency codes. "
            "If the user says \"달러\" assume USD, \"엔\" assume JPY, \"원\" assume KRW, "
            "\"유로\" assume EUR, \"위안\" assume CNY, \"파운드\" assume GBP."
        )

    async def try_execute(self, response: str, context: ToolContext) -> str | None:
        match = self.PATTERN.search(response)
        if not match:
            return None

        try:
            amount = float(match.group(1).strip())
        except ValueError:
            amount = 1.0
        from_cur = match.group(2).strip().upper()
        to_cur = match.group(3).strip().upper()

        logger.info(f"Tool called: [EXCHANGE:{amount},{from_cur},{to_cur}]")

        rate = await self._fetch_rate(from_cur, to_cur)

        if rate is not None:
            result = amount * rate
            from_name = CURRENCY_NAMES.get(from_cur, from_cur)
            to_name = CURRENCY_NAMES.get(to_cur, to_cur)
            return (
                f"Exchange rate result:\n"
                f"- {amount:,.2f} {from_cur} ({from_name}) = {result:,.2f} {to_cur} ({to_name})\n"
                f"- Rate: 1 {from_cur} = {rate:,.4f} {to_cur}"
            )
        else:
            return f"Failed to get exchange rate for {from_cur} → {to_cur}. Please check the currency codes."

    async def _fetch_rate(self, from_cur: str, to_cur: str) -> float | None:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(EXCHANGE_API_URL.format(base=from_cur)) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    if data.get("result") != "success":
                        return None
                    return data["rates"].get(to_cur)
        except Exception as e:
            logger.warning(f"Exchange rate API call failed ({from_cur} → {to_cur}): {e}")
            return None
