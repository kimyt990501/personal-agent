"""Handler for /email command."""

from discord import Message

from src.utils.email import send_email
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

USAGE = (
    "사용법: `/email <provider> <수신자> <제목> <본문>`\n"
    "- provider: `gmail` 또는 `naver`\n"
    "예시:\n"
    "  `/email gmail abc@naver.com 회의 안내 내일 2시에 회의합니다`\n"
    "  `/email naver abc@gmail.com 테스트 안녕하세요 테스트입니다`"
)


class EmailHandler:
    """Handler for direct /email command (no LLM, immediate send)."""

    async def handle(self, message: Message, user_id: str, content: str):
        """Handle /email command."""
        # Strip "/email" prefix and split into parts
        args = content[7:].strip()  # len("/email ") == 7

        if not args:
            await message.reply(USAGE)
            return

        parts = args.split(None, 3)
        if len(parts) < 4:
            await message.reply(f"❌ 인자가 부족합니다.\n\n{USAGE}")
            return

        provider, to, subject, body = parts
        provider = provider.lower()

        if provider not in ("gmail", "naver"):
            await message.reply(f"❌ provider는 `gmail` 또는 `naver`만 지원합니다. (입력값: `{provider}`)")
            return

        # Show one-line summary before sending
        await message.reply(
            f"📧 발송 중...\n"
            f"- provider: {provider}\n"
            f"- 수신: {to}\n"
            f"- 제목: {subject}"
        )

        logger.info(f"Sending email via /email command: provider={provider}, to={to}, user={user_id}")
        result = await send_email(provider, to, subject, body)

        if result["success"]:
            await message.reply(f"✅ 이메일을 발송했습니다.\n- 수신: {to}\n- 제목: {subject}")
        else:
            await message.reply(f"❌ 이메일 발송 실패: {result['message']}")
