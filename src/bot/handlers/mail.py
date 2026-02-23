"""Handler for /mail command."""

from discord import Message

from src.db import DB
from src.utils.email import check_new_mail
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

USAGE = (
    "사용법:\n"
    "- `/mail` — 현재 읽지 않은 메일 목록 확인\n"
    "- `/mail check` — 지금 즉시 메일 확인\n"
    "- `/mail on` — 자동 알림 활성화\n"
    "- `/mail off` — 자동 알림 비활성화"
)


class MailHandler:
    """Handler for /mail command."""

    def __init__(self, db: DB):
        self.db = db

    async def handle(self, message: Message, user_id: str, content: str):
        """Handle /mail command."""
        args = content[5:].strip().lower()  # strip "/mail"

        if not args or args == "check":
            await self._check_and_reply(message, user_id)
        elif args == "on":
            await self.db.mail.set_enabled(user_id, True)
            await message.reply("✅ 메일 자동 알림이 활성화되었습니다.")
            logger.info(f"Mail notifications enabled for user {user_id}")
        elif args == "off":
            await self.db.mail.set_enabled(user_id, False)
            await message.reply("🔕 메일 자동 알림이 비활성화되었습니다.")
            logger.info(f"Mail notifications disabled for user {user_id}")
        else:
            await message.reply(USAGE)

    async def _check_and_reply(self, message: Message, user_id: str):
        """Check unread mail for all providers and reply with results."""
        async with message.channel.typing():
            sections = []
            for provider in ("gmail", "naver"):
                mails = await check_new_mail(provider)
                if mails:
                    lines = [f"[{provider.upper()}]"]
                    for i, m in enumerate(mails, 1):
                        lines.append(f"{i}. {m['from']} - {m['subject']} ({m['date']})")
                    sections.append("\n".join(lines))

            if sections:
                body = "\n\n".join(sections)
                await message.reply(f"📬 읽지 않은 메일:\n\n{body}")
            else:
                await message.reply("📭 새 메일이 없습니다.")

    @staticmethod
    def format_mail_notification(gmail_mails: list[dict], naver_mails: list[dict]) -> str:
        """Format mail notification message for DM."""
        sections = []
        for label, mails in (("[Gmail]", gmail_mails), ("[Naver]", naver_mails)):
            if mails:
                lines = [label]
                for i, m in enumerate(mails, 1):
                    lines.append(f"{i}. {m['from']} - {m['subject']} ({m['date']})")
                sections.append("\n".join(lines))
        return "📬 새 메일이 도착했습니다!\n\n" + "\n\n".join(sections)
