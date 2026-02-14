import aiohttp
from discord import Message

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


CURRENCY_NAMES = {
    "KRW": "한국 원",
    "USD": "미국 달러",
    "JPY": "일본 엔",
    "EUR": "유로",
    "GBP": "영국 파운드",
    "CNY": "중국 위안",
}

API_URL = "https://open.er-api.com/v6/latest/{base}"


class ExchangeHandler:
    """Handler for currency exchange rate commands."""

    async def handle(self, message: Message, content: str):
        """Handle exchange rate command."""
        parts = content[3:].strip().split()

        if len(parts) < 2:
            await message.reply(
                "사용법: `/ex <금액> <from> <to>` 또는 `/ex <from> <to>`\n"
                "예: `/ex 100 USD KRW`, `/ex JPY KRW`\n\n"
                "**주요 통화:** " + ", ".join(f"`{k}` ({v})" for k, v in CURRENCY_NAMES.items())
            )
            return

        # Parse: /ex [amount] FROM TO
        try:
            amount = float(parts[0])
            from_cur = parts[1].upper()
            to_cur = parts[2].upper()
        except (ValueError, IndexError):
            amount = 1.0
            from_cur = parts[0].upper()
            to_cur = parts[1].upper()

        async with message.channel.typing():
            try:
                rate = await self._fetch_rate(from_cur, to_cur)
                if rate is None:
                    await message.reply("환율 정보를 가져오지 못했어요. 통화 코드를 확인해주세요.")
                    return

                result = amount * rate
                from_name = CURRENCY_NAMES.get(from_cur, from_cur)
                to_name = CURRENCY_NAMES.get(to_cur, to_cur)

                await message.reply(
                    f"**{from_name} → {to_name}**\n"
                    f"{amount:,.2f} {from_cur} = **{result:,.2f} {to_cur}**\n"
                    f"(1 {from_cur} = {rate:,.4f} {to_cur})"
                )
            except Exception as e:
                await message.reply(f"환율 조회 중 오류가 발생했습니다: {str(e)}")

    async def _fetch_rate(self, from_cur: str, to_cur: str) -> float | None:
        """Fetch exchange rate from API."""
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL.format(base=from_cur)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if data.get("result") != "success":
                    return None
                return data["rates"].get(to_cur)
