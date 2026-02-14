"""Handler for daily briefing commands."""

from discord import Message

from src.db import DB
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class BriefingHandler:
    """Handler for briefing commands (/briefing)."""

    def __init__(self, db: DB):
        self.db = db

    async def handle(self, message: Message, user_id: str, args: str):
        """Handle /briefing command."""
        args = args.strip()

        if not args:
            # Show current settings
            await self._show_settings(message, user_id)
        elif args == "on":
            await self.db.briefing.set_settings(user_id, enabled=True)
            await message.reply("✅ 브리핑이 활성화되었습니다.")
            logger.info(f"Briefing enabled for user {user_id}")
        elif args == "off":
            await self.db.briefing.set_settings(user_id, enabled=False)
            await message.reply("🔕 브리핑이 비활성화되었습니다.")
            logger.info(f"Briefing disabled for user {user_id}")
        elif args.startswith("time "):
            time = args[5:].strip()
            # Basic validation
            if ":" not in time or len(time.split(":")) != 2:
                await message.reply("❌ 시간 형식이 올바르지 않습니다. 예: `08:00`")
                return
            await self.db.briefing.set_settings(user_id, time=time)
            await message.reply(f"⏰ 브리핑 시간이 {time}로 설정되었습니다.")
            logger.info(f"Briefing time set to {time} for user {user_id}")
        elif args.startswith("city "):
            city = args[5:].strip()
            await self.db.briefing.set_settings(user_id, city=city)
            await message.reply(f"🌍 브리핑 도시가 {city}로 설정되었습니다.")
            logger.info(f"Briefing city set to {city} for user {user_id}")
        else:
            await message.reply(
                "사용법:\n"
                "- `/briefing` - 현재 설정 확인\n"
                "- `/briefing on` - 브리핑 활성화\n"
                "- `/briefing off` - 브리핑 비활성화\n"
                "- `/briefing time 07:00` - 시간 변경\n"
                "- `/briefing city 부산` - 도시 변경"
            )

    async def _show_settings(self, message: Message, user_id: str):
        """Show current briefing settings."""
        settings = await self.db.briefing.get_settings(user_id)

        if settings is None:
            # No settings yet, show defaults
            await message.reply(
                "📋 **브리핑 설정** (기본값)\n"
                "- 상태: ✅ 활성화\n"
                "- 시간: 08:00\n"
                "- 도시: 서울\n\n"
                "설정을 변경하려면 `/briefing` 명령어를 사용하세요."
            )
        else:
            status = "✅ 활성화" if settings["enabled"] else "🔕 비활성화"
            await message.reply(
                f"📋 **브리핑 설정**\n"
                f"- 상태: {status}\n"
                f"- 시간: {settings['time']}\n"
                f"- 도시: {settings['city']}\n\n"
                f"마지막 발송: {settings['last_sent'] or '없음'}"
            )
