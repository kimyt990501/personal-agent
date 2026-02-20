import re

import src.config as config
from src.bot.tools.base import Tool, ToolContext, ToolResult
from src.utils.email import send_email
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

EMAIL_SEND_PATTERN = re.compile(r"\[EMAIL_SEND:([^\]]+)\]")
EMAIL_CONFIRM_PATTERN = re.compile(r"\[EMAIL_CONFIRM\]")
EMAIL_CANCEL_PATTERN = re.compile(r"\[EMAIL_CANCEL\]")


class EmailTool(Tool):
    """Tool for sending emails via SMTP with a 2-step confirmation flow."""

    def __init__(self):
        self._pending_drafts: dict[str, dict] = {}

    @property
    def name(self) -> str:
        return "email"

    @property
    def description(self) -> str:
        return (
            "- Email: When the user wants to send an email (이메일 보내줘, 메일 보내줘, 메일 써줘), "
            "you MUST output [EMAIL_SEND:provider|to|subject|body] tag. "
            "You CANNOT send emails directly - you MUST use this tag.\n"
            "  Example: [EMAIL_SEND:gmail|friend@naver.com|회의 참석 요청|안녕하세요, 내일 회의에 참석 부탁드립니다.]\n"
            "  Example: [EMAIL_SEND:naver|abc@gmail.com|프로젝트 안내|프로젝트 진행 현황 공유드립니다.]\n"
            "  provider: naver or gmail (네이버→naver, 지메일→gmail, 미지정 시 빈칸)\n"
            "  - After draft preview, user confirms → [EMAIL_CONFIRM], user cancels → [EMAIL_CANCEL]"
        )

    @property
    def usage_rules(self) -> str:
        return (
            "- CRITICAL: You cannot send emails by yourself. When the user asks to send an email, "
            "you MUST output the [EMAIL_SEND:...] tag. NEVER pretend you sent an email without using the tag. "
            "After the draft is shown, output [EMAIL_CONFIRM] only when the user explicitly says 보내줘/응/확인."
        )

    async def try_execute(self, response: str, context: ToolContext) -> "str | ToolResult | None":
        # Try EMAIL_SEND
        match = EMAIL_SEND_PATTERN.search(response)
        if match:
            raw = match.group(1)
            parts = raw.split("|", 3)
            if len(parts) < 4:
                return ToolResult(
                    result="이메일 형식 오류: [EMAIL_SEND:provider|to|subject|body] 형식으로 작성해주세요.",
                    stop_loop=True,
                )

            provider, to, subject, body = parts
            provider = provider.strip()
            to = to.strip()
            subject = subject.strip()
            body = body.strip()

            if not provider:
                provider = config.EMAIL_DEFAULT_PROVIDER

            self._pending_drafts[context.user_id] = {
                "provider": provider,
                "to": to,
                "subject": subject,
                "body": body,
            }

            logger.info(f"Email draft created for user {context.user_id} → {to}")
            preview = (
                f"📧 **이메일 초안**\n"
                f"- 발신: {provider}\n"
                f"- 수신: {to}\n"
                f"- 제목: {subject}\n"
                f"- 본문:\n{body}\n\n"
                f"발송할까요? (\"응\" / \"아니\")"
            )
            return ToolResult(result=preview, stop_loop=True)

        # Try EMAIL_CONFIRM
        match = EMAIL_CONFIRM_PATTERN.search(response)
        if match:
            draft = self._pending_drafts.get(context.user_id)
            if not draft:
                return "발송할 이메일 초안이 없습니다. 먼저 이메일 내용을 작성해주세요."

            logger.info(f"Sending email for user {context.user_id} via {draft['provider']}")
            result = await send_email(
                draft["provider"], draft["to"], draft["subject"], draft["body"]
            )
            del self._pending_drafts[context.user_id]

            if result["success"]:
                return f"✅ 이메일을 발송했습니다.\n- 수신: {draft['to']}\n- 제목: {draft['subject']}"
            else:
                return f"❌ 이메일 발송 실패: {result['message']}"

        # Try EMAIL_CANCEL
        match = EMAIL_CANCEL_PATTERN.search(response)
        if match:
            if context.user_id in self._pending_drafts:
                del self._pending_drafts[context.user_id]
                logger.info(f"Email draft cancelled for user {context.user_id}")
                return "이메일 발송이 취소되었습니다."
            return "취소할 이메일 초안이 없습니다."

        return None
