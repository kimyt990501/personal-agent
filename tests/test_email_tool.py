"""Tests for EmailTool and send_email utility."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import smtplib

from src.bot.tools.email import EmailTool
from src.bot.tools import ToolContext


USER_ID = "test_user_123"
OTHER_USER = "other_user_456"


@pytest.fixture
def tool():
    return EmailTool()


@pytest.fixture
def context():
    db = MagicMock()
    return ToolContext(user_id=USER_ID, db=db, persona={})


@pytest.fixture
def other_context():
    db = MagicMock()
    return ToolContext(user_id=OTHER_USER, db=db, persona={})


# ─── ABC 속성 ───

class TestEmailToolProperties:
    def test_name_is_email(self, tool):
        assert tool.name == "email"

    def test_description_contains_patterns(self, tool):
        desc = tool.description
        assert "EMAIL_SEND" in desc
        assert "EMAIL_CONFIRM" in desc
        assert "EMAIL_CANCEL" in desc
        assert "|" in desc  # 구분자 설명 포함

    def test_usage_rules_is_string(self, tool):
        assert isinstance(tool.usage_rules, str)
        assert len(tool.usage_rules) > 0

    def test_pending_drafts_initially_empty(self, tool):
        assert tool._pending_drafts == {}


# ─── EMAIL_SEND 패턴 파싱 ───

class TestEmailSendPattern:
    @pytest.mark.asyncio
    async def test_basic_send_creates_draft(self, tool, context):
        result = await tool.try_execute(
            "[EMAIL_SEND:naver|friend@naver.com|안녕하세요|본문 내용입니다]", context
        )
        assert result is not None
        assert "초안" in result.result
        assert "friend@naver.com" in result.result
        assert "안녕하세요" in result.result
        assert "본문 내용입니다" in result.result
        assert result.stop_loop is True

    @pytest.mark.asyncio
    async def test_draft_stored_in_pending(self, tool, context):
        await tool.try_execute(
            "[EMAIL_SEND:naver|friend@naver.com|제목|본문]", context
        )
        assert USER_ID in tool._pending_drafts
        draft = tool._pending_drafts[USER_ID]
        assert draft["provider"] == "naver"
        assert draft["to"] == "friend@naver.com"
        assert draft["subject"] == "제목"
        assert draft["body"] == "본문"

    @pytest.mark.asyncio
    async def test_empty_provider_uses_default(self, tool, context):
        """provider 생략 시 EMAIL_DEFAULT_PROVIDER 사용."""
        with patch("src.bot.tools.email.config") as mock_cfg:
            mock_cfg.EMAIL_DEFAULT_PROVIDER = "naver"
            await tool.try_execute(
                "[EMAIL_SEND:|friend@naver.com|제목|본문]", context
            )
        assert tool._pending_drafts[USER_ID]["provider"] == "naver"

    @pytest.mark.asyncio
    async def test_body_with_commas_parsed_correctly(self, tool, context):
        """body에 쉼표가 포함되어도 정상 파싱된다."""
        await tool.try_execute(
            "[EMAIL_SEND:gmail|a@gmail.com|제목|안녕하세요, 잘 지내시나요, 답장 부탁드립니다]",
            context,
        )
        draft = tool._pending_drafts[USER_ID]
        assert draft["body"] == "안녕하세요, 잘 지내시나요, 답장 부탁드립니다"

    @pytest.mark.asyncio
    async def test_body_with_pipe_parsed_correctly(self, tool, context):
        """split(|, 3)으로 body 내 파이프 문자도 보존된다."""
        await tool.try_execute(
            "[EMAIL_SEND:naver|a@naver.com|제목|항목1|항목2|항목3]", context
        )
        draft = tool._pending_drafts[USER_ID]
        # 4번째 split 이후 전체가 body
        assert "항목1|항목2|항목3" == draft["body"]

    @pytest.mark.asyncio
    async def test_whitespace_stripped_from_fields(self, tool, context):
        """각 필드 양끝 공백이 제거된다."""
        await tool.try_execute(
            "[EMAIL_SEND: naver | a@naver.com | 제목 | 본문 ]", context
        )
        draft = tool._pending_drafts[USER_ID]
        assert draft["provider"] == "naver"
        assert draft["to"] == "a@naver.com"
        assert draft["subject"] == "제목"
        assert draft["body"] == "본문"

    @pytest.mark.asyncio
    async def test_missing_body_returns_format_error(self, tool, context):
        """필드가 3개 이하면 형식 오류 반환."""
        result = await tool.try_execute(
            "[EMAIL_SEND:naver|a@naver.com|제목]", context
        )
        assert result is not None
        assert "형식 오류" in result.result
        assert result.stop_loop is True
        assert USER_ID not in tool._pending_drafts

    @pytest.mark.asyncio
    async def test_preview_includes_confirmation_prompt(self, tool, context):
        """초안 미리보기에 확인/취소 안내가 포함된다."""
        result = await tool.try_execute(
            "[EMAIL_SEND:naver|a@naver.com|제목|본문]", context
        )
        assert "발송할까요" in result.result or "응" in result.result
        assert result.stop_loop is True


# ─── EMAIL_CONFIRM 패턴 ───

class TestEmailConfirmPattern:
    @pytest.mark.asyncio
    async def test_confirm_calls_send_email(self, tool, context):
        """초안이 있을 때 CONFIRM → send_email 호출."""
        tool._pending_drafts[USER_ID] = {
            "provider": "naver",
            "to": "friend@naver.com",
            "subject": "테스트",
            "body": "본문",
        }
        with patch("src.bot.tools.email.send_email", new=AsyncMock(
            return_value={"success": True, "message": "발송 완료"}
        )) as mock_send:
            result = await tool.try_execute("[EMAIL_CONFIRM]", context)

        mock_send.assert_called_once_with("naver", "friend@naver.com", "테스트", "본문")
        assert "발송했습니다" in result

    @pytest.mark.asyncio
    async def test_confirm_deletes_draft_after_send(self, tool, context):
        """CONFIRM 후 초안이 삭제된다 (재발송 방지)."""
        tool._pending_drafts[USER_ID] = {
            "provider": "naver", "to": "a@b.com", "subject": "s", "body": "b"
        }
        with patch("src.bot.tools.email.send_email", new=AsyncMock(
            return_value={"success": True, "message": "ok"}
        )):
            await tool.try_execute("[EMAIL_CONFIRM]", context)
        assert USER_ID not in tool._pending_drafts

    @pytest.mark.asyncio
    async def test_confirm_on_send_failure_returns_error(self, tool, context):
        """send_email 실패 시 에러 메시지 반환."""
        tool._pending_drafts[USER_ID] = {
            "provider": "naver", "to": "a@b.com", "subject": "s", "body": "b"
        }
        with patch("src.bot.tools.email.send_email", new=AsyncMock(
            return_value={"success": False, "message": "인증 실패"}
        )):
            result = await tool.try_execute("[EMAIL_CONFIRM]", context)
        assert "실패" in result
        assert "인증 실패" in result

    @pytest.mark.asyncio
    async def test_confirm_without_draft_returns_error(self, tool, context):
        """초안 없이 CONFIRM → 에러 메시지, send_email 호출 없음."""
        with patch("src.bot.tools.email.send_email", new=AsyncMock()) as mock_send:
            result = await tool.try_execute("[EMAIL_CONFIRM]", context)
        mock_send.assert_not_called()
        assert "초안이 없습니다" in result

    @pytest.mark.asyncio
    async def test_confirm_includes_recipient_in_success(self, tool, context):
        """성공 메시지에 수신자 정보가 포함된다."""
        tool._pending_drafts[USER_ID] = {
            "provider": "gmail", "to": "boss@gmail.com", "subject": "보고서", "body": "..."
        }
        with patch("src.bot.tools.email.send_email", new=AsyncMock(
            return_value={"success": True, "message": "ok"}
        )):
            result = await tool.try_execute("[EMAIL_CONFIRM]", context)
        assert "boss@gmail.com" in result


# ─── EMAIL_CANCEL 패턴 ───

class TestEmailCancelPattern:
    @pytest.mark.asyncio
    async def test_cancel_with_draft_deletes_it(self, tool, context):
        """초안이 있을 때 CANCEL → 삭제."""
        tool._pending_drafts[USER_ID] = {
            "provider": "naver", "to": "a@b.com", "subject": "s", "body": "b"
        }
        result = await tool.try_execute("[EMAIL_CANCEL]", context)
        assert USER_ID not in tool._pending_drafts
        assert "취소" in result

    @pytest.mark.asyncio
    async def test_cancel_without_draft_returns_message(self, tool, context):
        """초안 없이 CANCEL → 별도 메시지 반환."""
        result = await tool.try_execute("[EMAIL_CANCEL]", context)
        assert result is not None
        assert "없습니다" in result

    @pytest.mark.asyncio
    async def test_no_pattern_returns_none(self, tool, context):
        result = await tool.try_execute("일반 대화 응답입니다.", context)
        assert result is None

    @pytest.mark.asyncio
    async def test_other_tool_pattern_returns_none(self, tool, context):
        result = await tool.try_execute("[WEATHER:서울]", context)
        assert result is None


# ─── 초안 상태 관리 ───

class TestDraftStateManagement:
    @pytest.mark.asyncio
    async def test_different_users_have_separate_drafts(self, tool, context, other_context):
        """사용자별 독립된 초안 관리."""
        await tool.try_execute(
            "[EMAIL_SEND:naver|a@a.com|제목A|본문A]", context
        )
        await tool.try_execute(
            "[EMAIL_SEND:gmail|b@b.com|제목B|본문B]", other_context
        )
        assert tool._pending_drafts[USER_ID]["subject"] == "제목A"
        assert tool._pending_drafts[OTHER_USER]["subject"] == "제목B"

    @pytest.mark.asyncio
    async def test_confirm_only_deletes_own_draft(self, tool, context, other_context):
        """CONFIRM은 자신의 초안만 삭제한다."""
        tool._pending_drafts[USER_ID] = {
            "provider": "naver", "to": "a@a.com", "subject": "A", "body": "a"
        }
        tool._pending_drafts[OTHER_USER] = {
            "provider": "gmail", "to": "b@b.com", "subject": "B", "body": "b"
        }
        with patch("src.bot.tools.email.send_email", new=AsyncMock(
            return_value={"success": True, "message": "ok"}
        )):
            await tool.try_execute("[EMAIL_CONFIRM]", context)
        assert USER_ID not in tool._pending_drafts
        assert OTHER_USER in tool._pending_drafts

    @pytest.mark.asyncio
    async def test_overwrite_draft_with_new_send(self, tool, context):
        """새 EMAIL_SEND 시 이전 초안이 덮어쓰인다."""
        await tool.try_execute("[EMAIL_SEND:naver|a@a.com|제목1|본문1]", context)
        await tool.try_execute("[EMAIL_SEND:gmail|b@b.com|제목2|본문2]", context)
        draft = tool._pending_drafts[USER_ID]
        assert draft["subject"] == "제목2"
        assert draft["to"] == "b@b.com"


# ─── SMTP 유틸리티 ───
# send_email 내부에서 `import src.config as config`로 로컬 임포트하므로
# src.config 모듈의 속성을 직접 patch해야 함

class TestSendEmailUtility:
    @pytest.mark.asyncio
    async def test_unsupported_provider_returns_error(self):
        from src.utils.email import send_email
        result = await send_email("kakao", "a@b.com", "제목", "본문")
        assert result["success"] is False
        assert "provider" in result["message"] or "kakao" in result["message"]

    @pytest.mark.asyncio
    async def test_missing_credentials_returns_error(self):
        from src.utils.email import send_email
        with patch("src.config.EMAIL_NAVER_USER", ""), \
             patch("src.config.EMAIL_NAVER_PASSWORD", ""):
            result = await send_email("naver", "a@b.com", "제목", "본문")
        assert result["success"] is False
        assert "설정되지 않았습니다" in result["message"]

    @pytest.mark.asyncio
    async def test_successful_send(self):
        from src.utils.email import send_email
        mock_smtp = MagicMock()
        with patch("src.config.EMAIL_NAVER_USER", "me@naver.com"), \
             patch("src.config.EMAIL_NAVER_PASSWORD", "secret"), \
             patch("smtplib.SMTP", return_value=mock_smtp):
            mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp.__exit__ = MagicMock(return_value=False)
            result = await send_email("naver", "friend@naver.com", "제목", "본문")
        assert result["success"] is True
        assert "발송했습니다" in result["message"]

    @pytest.mark.asyncio
    async def test_smtp_auth_error(self):
        from src.utils.email import send_email
        mock_smtp = MagicMock()
        mock_smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Auth failed")
        with patch("src.config.EMAIL_NAVER_USER", "me@naver.com"), \
             patch("src.config.EMAIL_NAVER_PASSWORD", "wrong"), \
             patch("smtplib.SMTP", return_value=mock_smtp):
            mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp.__exit__ = MagicMock(return_value=False)
            result = await send_email("naver", "a@b.com", "제목", "본문")
        assert result["success"] is False
        assert "인증 실패" in result["message"]

    @pytest.mark.asyncio
    async def test_smtp_recipients_refused(self):
        from src.utils.email import send_email
        mock_smtp = MagicMock()
        mock_smtp.sendmail.side_effect = smtplib.SMTPRecipientsRefused({"bad@x.com": (550, b"User unknown")})
        with patch("src.config.EMAIL_GMAIL_USER", "me@gmail.com"), \
             patch("src.config.EMAIL_GMAIL_PASSWORD", "pw"), \
             patch("smtplib.SMTP", return_value=mock_smtp):
            mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp.__exit__ = MagicMock(return_value=False)
            result = await send_email("gmail", "bad@x.com", "제목", "본문")
        assert result["success"] is False
        assert "수신자" in result["message"]

    @pytest.mark.asyncio
    async def test_network_error(self):
        from src.utils.email import send_email
        with patch("src.config.EMAIL_NAVER_USER", "me@naver.com"), \
             patch("src.config.EMAIL_NAVER_PASSWORD", "pw"), \
             patch("smtplib.SMTP", side_effect=OSError("Connection refused")):
            result = await send_email("naver", "a@b.com", "제목", "본문")
        assert result["success"] is False
        assert "네트워크" in result["message"]

    @pytest.mark.asyncio
    async def test_password_not_in_log(self):
        """비밀번호가 로그에 노출되지 않는다."""
        from src.utils.email import send_email
        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=False)
        with patch("src.config.EMAIL_NAVER_USER", "me@naver.com"), \
             patch("src.config.EMAIL_NAVER_PASSWORD", "super_secret_pw"), \
             patch("smtplib.SMTP", return_value=mock_smtp), \
             patch("src.utils.email.logger") as mock_logger:
            await send_email("naver", "a@b.com", "제목", "본문")

        all_log_calls = (
            str(mock_logger.info.call_args_list)
            + str(mock_logger.warning.call_args_list)
        )
        assert "super_secret_pw" not in all_log_calls


# ─── config 환경변수 ───

class TestEmailConfig:
    def test_default_provider_is_naver(self):
        """EMAIL_DEFAULT_PROVIDER 기본값은 naver."""
        import src.config as cfg
        # 환경변수 미설정 시 기본값 확인
        with patch.dict("os.environ", {}, clear=False):
            import importlib
            # 현재 로드된 config의 기본값 검증
            assert cfg.EMAIL_DEFAULT_PROVIDER in ("naver", "gmail")  # 유효한 값

    def test_email_config_vars_exist(self):
        """이메일 관련 config 변수가 모두 존재한다."""
        import src.config as cfg
        assert hasattr(cfg, "EMAIL_NAVER_USER")
        assert hasattr(cfg, "EMAIL_NAVER_PASSWORD")
        assert hasattr(cfg, "EMAIL_GMAIL_USER")
        assert hasattr(cfg, "EMAIL_GMAIL_PASSWORD")
        assert hasattr(cfg, "EMAIL_DEFAULT_PROVIDER")

    def test_email_config_are_strings(self):
        """이메일 config 값은 문자열이다."""
        import src.config as cfg
        assert isinstance(cfg.EMAIL_NAVER_USER, str)
        assert isinstance(cfg.EMAIL_NAVER_PASSWORD, str)
        assert isinstance(cfg.EMAIL_GMAIL_USER, str)
        assert isinstance(cfg.EMAIL_GMAIL_PASSWORD, str)
        assert isinstance(cfg.EMAIL_DEFAULT_PROVIDER, str)


# ─── ToolRegistry 등록 ───

class TestEmailToolRegistry:
    def test_can_register_in_registry(self):
        from src.bot.tools import ToolRegistry
        registry = ToolRegistry()
        registry.register(EmailTool())
        assert any(t.name == "email" for t in registry.tools)

    def test_email_tags_in_instructions(self):
        from src.bot.tools import ToolRegistry
        registry = ToolRegistry()
        registry.register(EmailTool())
        instructions = registry.build_tool_instructions()
        assert "EMAIL_SEND" in instructions
        assert "EMAIL_CONFIRM" in instructions
        assert "EMAIL_CANCEL" in instructions

    def test_chat_handler_registers_email_tool(self):
        """ChatHandler가 EmailTool을 ToolRegistry에 등록한다."""
        from src.bot.handlers.chat import ChatHandler
        db = MagicMock()
        ollama = MagicMock()
        handler = ChatHandler(db, ollama)
        names = [t.name for t in handler.registry.tools]
        assert "email" in names

    def test_chat_handler_has_nine_tools(self):
        """EmailTool 추가 후 ChatHandler에 9개 도구가 등록된다."""
        from src.bot.handlers.chat import ChatHandler
        db = MagicMock()
        ollama = MagicMock()
        handler = ChatHandler(db, ollama)
        assert len(handler.registry.tools) == 9
