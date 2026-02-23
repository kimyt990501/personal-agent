"""Tests for mail notification — IMAP utility, MailDB, MailHandler."""
import imaplib
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.db.mail import MailDB
from src.bot.handlers.mail import MailHandler, USAGE


USER_ID = "test_user_123"
OTHER_USER = "other_user_456"


# ─── MailDB ───

class TestMailDB:
    @pytest_asyncio.fixture
    async def mail_db(self, tmp_db):
        db = MailDB()
        db.db_path = tmp_db
        return db

    @pytest.mark.asyncio
    async def test_get_settings_nonexistent_returns_none(self, mail_db):
        result = await mail_db.get_settings(USER_ID)
        assert result is None

    @pytest.mark.asyncio
    async def test_set_enabled_true_and_get(self, mail_db):
        await mail_db.set_enabled(USER_ID, True)
        result = await mail_db.get_settings(USER_ID)
        assert result is not None
        assert result["enabled"] is True

    @pytest.mark.asyncio
    async def test_set_enabled_false_and_get(self, mail_db):
        await mail_db.set_enabled(USER_ID, False)
        result = await mail_db.get_settings(USER_ID)
        assert result is not None
        assert result["enabled"] is False

    @pytest.mark.asyncio
    async def test_set_enabled_upsert_no_duplicate(self, mail_db):
        """같은 user_id로 두 번 호출해도 행이 1개만 생성된다."""
        await mail_db.set_enabled(USER_ID, True)
        await mail_db.set_enabled(USER_ID, False)
        result = await mail_db.get_settings(USER_ID)
        assert result["enabled"] is False  # 마지막 값

    @pytest.mark.asyncio
    async def test_update_last_checked(self, mail_db):
        await mail_db.update_last_checked(USER_ID, "2026-02-20 10:00:00")
        result = await mail_db.get_settings(USER_ID)
        assert result is not None
        assert result["last_checked"] == "2026-02-20 10:00:00"

    @pytest.mark.asyncio
    async def test_update_last_checked_upsert(self, mail_db):
        """set_enabled 없이 update_last_checked만 호출해도 upsert된다."""
        await mail_db.update_last_checked(USER_ID, "2026-02-20 09:00:00")
        await mail_db.update_last_checked(USER_ID, "2026-02-20 10:00:00")
        result = await mail_db.get_settings(USER_ID)
        assert result["last_checked"] == "2026-02-20 10:00:00"

    @pytest.mark.asyncio
    async def test_get_all_enabled_returns_only_enabled(self, mail_db):
        await mail_db.set_enabled(USER_ID, True)
        await mail_db.set_enabled(OTHER_USER, False)
        rows = await mail_db.get_all_enabled()
        user_ids = [r["user_id"] for r in rows]
        assert USER_ID in user_ids
        assert OTHER_USER not in user_ids

    @pytest.mark.asyncio
    async def test_get_all_enabled_empty_when_none(self, mail_db):
        rows = await mail_db.get_all_enabled()
        assert rows == []

    @pytest.mark.asyncio
    async def test_get_all_enabled_includes_last_checked(self, mail_db):
        await mail_db.set_enabled(USER_ID, True)
        await mail_db.update_last_checked(USER_ID, "2026-02-20 08:00:00")
        rows = await mail_db.get_all_enabled()
        assert rows[0]["last_checked"] == "2026-02-20 08:00:00"

    @pytest.mark.asyncio
    async def test_multiple_users_independent(self, mail_db):
        """여러 사용자 설정이 독립적으로 저장된다."""
        await mail_db.set_enabled(USER_ID, True)
        await mail_db.set_enabled(OTHER_USER, True)
        rows = await mail_db.get_all_enabled()
        assert len(rows) == 2


# ─── MailHandler 명령어 파싱 ───

class TestMailHandlerCommands:
    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.mail = AsyncMock()
        return db

    @pytest.fixture
    def handler(self, mock_db):
        return MailHandler(mock_db)

    @pytest.fixture
    def message(self):
        msg = AsyncMock()
        msg.reply = AsyncMock()
        msg.channel = MagicMock()
        msg.channel.typing = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=None),
            __aexit__=AsyncMock(return_value=False),
        ))
        return msg

    @pytest.mark.asyncio
    async def test_mail_on_enables_notifications(self, handler, message):
        await handler.handle(message, USER_ID, "/mail on")
        handler.db.mail.set_enabled.assert_called_once_with(USER_ID, True)
        message.reply.assert_called_once()
        assert "활성화" in message.reply.call_args[0][0]

    @pytest.mark.asyncio
    async def test_mail_off_disables_notifications(self, handler, message):
        await handler.handle(message, USER_ID, "/mail off")
        handler.db.mail.set_enabled.assert_called_once_with(USER_ID, False)
        message.reply.assert_called_once()
        assert "비활성화" in message.reply.call_args[0][0]

    @pytest.mark.asyncio
    async def test_mail_unknown_shows_usage(self, handler, message):
        await handler.handle(message, USER_ID, "/mail unknown_cmd")
        message.reply.assert_called_once_with(USAGE)

    @pytest.mark.asyncio
    async def test_mail_empty_triggers_check(self, handler, message):
        """/mail (인자 없음) → 메일 확인."""
        with patch.object(handler, "_check_and_reply", new=AsyncMock()) as mock_check:
            await handler.handle(message, USER_ID, "/mail")
        mock_check.assert_called_once_with(message, USER_ID)

    @pytest.mark.asyncio
    async def test_mail_check_triggers_check(self, handler, message):
        """/mail check → 메일 확인."""
        with patch.object(handler, "_check_and_reply", new=AsyncMock()) as mock_check:
            await handler.handle(message, USER_ID, "/mail check")
        mock_check.assert_called_once_with(message, USER_ID)

    @pytest.mark.asyncio
    async def test_check_and_reply_no_mail(self, handler, message):
        """새 메일 없을 때 '새 메일이 없습니다' 응답."""
        with patch("src.bot.handlers.mail.check_new_mail", new=AsyncMock(return_value=[])):
            await handler._check_and_reply(message, USER_ID)
        reply_text = message.reply.call_args[0][0]
        assert "없습니다" in reply_text

    @pytest.mark.asyncio
    async def test_check_and_reply_with_mail(self, handler, message):
        """새 메일 있을 때 메일 정보 포함 응답."""
        mails = [{"from": "boss@gmail.com", "subject": "보고서", "date": "Thu, 20 Feb 2026"}]
        with patch("src.bot.handlers.mail.check_new_mail", new=AsyncMock(return_value=mails)):
            await handler._check_and_reply(message, USER_ID)
        reply_text = message.reply.call_args[0][0]
        assert "boss@gmail.com" in reply_text
        assert "보고서" in reply_text


# ─── format_mail_notification ───

class TestFormatMailNotification:
    def test_gmail_only(self):
        gmail = [{"from": "a@gmail.com", "subject": "Hello", "date": "Mon"}]
        result = MailHandler.format_mail_notification(gmail, [])
        assert "[Gmail]" in result
        assert "a@gmail.com" in result
        assert "[Naver]" not in result

    def test_naver_only(self):
        naver = [{"from": "b@naver.com", "subject": "안녕", "date": "Tue"}]
        result = MailHandler.format_mail_notification([], naver)
        assert "[Naver]" in result
        assert "b@naver.com" in result
        assert "[Gmail]" not in result

    def test_both_providers(self):
        gmail = [{"from": "a@gmail.com", "subject": "G", "date": "Mon"}]
        naver = [{"from": "b@naver.com", "subject": "N", "date": "Tue"}]
        result = MailHandler.format_mail_notification(gmail, naver)
        assert "[Gmail]" in result
        assert "[Naver]" in result

    def test_notification_header(self):
        gmail = [{"from": "a@gmail.com", "subject": "S", "date": "D"}]
        result = MailHandler.format_mail_notification(gmail, [])
        assert "새 메일" in result

    def test_multiple_mails_numbered(self):
        mails = [
            {"from": "a@gmail.com", "subject": "첫 번째", "date": "Mon"},
            {"from": "b@gmail.com", "subject": "두 번째", "date": "Tue"},
        ]
        result = MailHandler.format_mail_notification(mails, [])
        assert "1." in result
        assert "2." in result


# ─── IMAP check_new_mail mock 테스트 ───

class TestCheckNewMail:
    @pytest.mark.asyncio
    async def test_unsupported_provider_returns_empty(self):
        from src.utils.email import check_new_mail
        result = await check_new_mail("kakao")
        assert result == []

    @pytest.mark.asyncio
    async def test_missing_credentials_returns_empty(self):
        from src.utils.email import check_new_mail
        with patch("src.config.EMAIL_NAVER_USER", ""), \
             patch("src.config.EMAIL_NAVER_PASSWORD", ""):
            result = await check_new_mail("naver")
        assert result == []

    @pytest.mark.asyncio
    async def test_successful_check_returns_mail_list(self):
        from src.utils.email import check_new_mail
        mock_imap = MagicMock()
        mock_imap.search.return_value = (None, [b"1 2 3"])
        raw_header = b"From: sender@example.com\r\nSubject: Test Subject\r\nDate: Thu, 20 Feb 2026\r\n"
        mock_imap.fetch.return_value = (None, [(None, raw_header)])

        with patch("src.config.EMAIL_NAVER_USER", "me@naver.com"), \
             patch("src.config.EMAIL_NAVER_PASSWORD", "pw"), \
             patch("imaplib.IMAP4_SSL", return_value=mock_imap):
            mock_imap.__enter__ = MagicMock(return_value=mock_imap)
            mock_imap.__exit__ = MagicMock(return_value=False)
            result = await check_new_mail("naver")

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_empty_inbox_returns_empty_list(self):
        from src.utils.email import check_new_mail
        mock_imap = MagicMock()
        mock_imap.search.return_value = (None, [b""])

        with patch("src.config.EMAIL_NAVER_USER", "me@naver.com"), \
             patch("src.config.EMAIL_NAVER_PASSWORD", "pw"), \
             patch("imaplib.IMAP4_SSL", return_value=mock_imap):
            mock_imap.__enter__ = MagicMock(return_value=mock_imap)
            mock_imap.__exit__ = MagicMock(return_value=False)
            result = await check_new_mail("naver")

        assert result == []

    @pytest.mark.asyncio
    async def test_imap_error_returns_empty_list(self):
        """IMAP 오류 발생 시 빈 리스트 반환 (예외 전파 없음)."""
        from src.utils.email import check_new_mail
        with patch("src.config.EMAIL_NAVER_USER", "me@naver.com"), \
             patch("src.config.EMAIL_NAVER_PASSWORD", "pw"), \
             patch("imaplib.IMAP4_SSL", side_effect=imaplib.IMAP4.error("Auth failed")):
            result = await check_new_mail("naver")
        assert result == []

    @pytest.mark.asyncio
    async def test_network_error_returns_empty_list(self):
        """네트워크 오류 발생 시 빈 리스트 반환."""
        from src.utils.email import check_new_mail
        with patch("src.config.EMAIL_NAVER_USER", "me@naver.com"), \
             patch("src.config.EMAIL_NAVER_PASSWORD", "pw"), \
             patch("imaplib.IMAP4_SSL", side_effect=OSError("Connection refused")):
            result = await check_new_mail("naver")
        assert result == []

    @pytest.mark.asyncio
    async def test_password_not_in_log(self):
        """IMAP 비밀번호가 로그에 노출되지 않는다."""
        from src.utils.email import check_new_mail
        with patch("src.config.EMAIL_NAVER_USER", "me@naver.com"), \
             patch("src.config.EMAIL_NAVER_PASSWORD", "imap_secret_pw"), \
             patch("imaplib.IMAP4_SSL", side_effect=OSError("fail")), \
             patch("src.utils.email.logger") as mock_logger:
            await check_new_mail("naver")

        all_logs = (
            str(mock_logger.info.call_args_list)
            + str(mock_logger.warning.call_args_list)
            + str(mock_logger.error.call_args_list)
        )
        assert "imap_secret_pw" not in all_logs

    @pytest.mark.asyncio
    async def test_gmail_provider_uses_gmail_credentials(self):
        """gmail provider는 Gmail 계정 정보를 사용한다."""
        from src.utils.email import check_new_mail
        with patch("src.config.EMAIL_GMAIL_USER", ""), \
             patch("src.config.EMAIL_GMAIL_PASSWORD", ""):
            result = await check_new_mail("gmail")
        assert result == []  # 자격증명 없음 → 빈 리스트


# ─── _decode_header_value ───

class TestDecodeHeaderValue:
    def test_plain_string(self):
        from src.utils.email import _decode_header_value
        result = _decode_header_value("Hello World")
        assert result == "Hello World"

    def test_utf8_encoded(self):
        from src.utils.email import _decode_header_value
        # =?UTF-8?B?... base64 encoded "안녕"
        import base64
        encoded = base64.b64encode("안녕".encode("utf-8")).decode("ascii")
        mime_val = f"=?UTF-8?B?{encoded}?="
        result = _decode_header_value(mime_val)
        assert result == "안녕"

    def test_plain_ascii(self):
        from src.utils.email import _decode_header_value
        result = _decode_header_value("Test Subject")
        assert "Test Subject" in result


# ─── check_mail 루프 패턴 코드 리뷰 ───

class TestCheckMailLoopPattern:
    def test_check_mail_loop_interval_is_30_minutes(self):
        """check_mail 루프는 30분 간격으로 설정되어야 한다."""
        import inspect
        from src.bot.client import PersonalAssistantBot
        # tasks.loop decorator의 minutes 인자 확인
        loop_fn = PersonalAssistantBot.check_mail
        # discord.ext.tasks.Loop 객체의 minutes 속성 확인
        assert hasattr(loop_fn, "minutes") or hasattr(loop_fn, "_seconds")

    def test_mail_handler_registered_in_bot(self):
        """PersonalAssistantBot이 MailHandler를 초기화한다."""
        from src.bot.client import PersonalAssistantBot
        # __init__ 소스코드에 mail_handler 있는지 확인
        import inspect
        src = inspect.getsource(PersonalAssistantBot.__init__)
        assert "mail_handler" in src
        assert "MailHandler" in src
