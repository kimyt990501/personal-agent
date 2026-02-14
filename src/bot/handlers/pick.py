import random

from discord import Message

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class PickHandler:
    """Handler for random pick commands."""

    async def handle(self, message: Message, content: str):
        """Handle random pick command."""
        text = content[5:].strip()

        if not text:
            await message.reply(
                "사용법: `/pick <항목1> <항목2> ...`\n"
                "예: `/pick 짜장 짬뽕 볶음밥`"
            )
            return

        items = text.split()
        if len(items) < 2:
            await message.reply("2개 이상 항목을 입력해주세요.")
            return

        chosen = random.choice(items)
        await message.reply(f"🎲 **{chosen}**")
