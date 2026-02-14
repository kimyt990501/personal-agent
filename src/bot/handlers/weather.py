from discord import Message

from src.utils.weather import get_weather, format_weather
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class WeatherHandler:
    """Handler for weather commands."""

    async def handle(self, message: Message, content: str):
        """Handle weather command."""
        parts = content.split(maxsplit=1)

        # /w alone
        if len(parts) == 1 or not parts[1].strip():
            await message.reply(
                "**🌤️ 날씨 사용법**\n"
                "`/w <도시>` - 해당 도시 날씨 확인\n\n"
                "**예시**\n"
                "`/w 서울`\n"
                "`/w 부산`\n"
                "`/w Tokyo`"
            )
            return

        city = parts[1].strip()

        async with message.channel.typing():
            weather = await get_weather(city)

            if weather:
                await message.reply(format_weather(weather))
            else:
                await message.reply("날씨 정보를 가져오지 못했어요. 다시 시도해주세요.")
