"""SMTP/IMAP email utility."""

import asyncio
import imaplib
import smtplib
from email.header import decode_header
from email.mime.text import MIMEText

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

SMTP_SETTINGS = {
    "gmail": {"host": "smtp.gmail.com", "port": 587},
    "naver": {"host": "smtp.naver.com", "port": 587},
}

IMAP_SETTINGS = {
    "gmail": {"host": "imap.gmail.com", "port": 993},
    "naver": {"host": "imap.naver.com", "port": 993},
}


async def send_email(provider: str, to: str, subject: str, body: str) -> dict:
    """Send an email via SMTP. Returns {success: bool, message: str}."""
    import src.config as config

    settings = SMTP_SETTINGS.get(provider)
    if settings is None:
        return {"success": False, "message": f"지원하지 않는 provider: {provider}. naver 또는 gmail을 사용하세요."}

    if provider == "naver":
        user = config.EMAIL_NAVER_USER
        password = config.EMAIL_NAVER_PASSWORD
    else:
        user = config.EMAIL_GMAIL_USER
        password = config.EMAIL_GMAIL_PASSWORD

    if not user or not password:
        return {"success": False, "message": f"{provider} 계정 정보가 설정되지 않았습니다. .env 파일을 확인해주세요."}

    def _send() -> dict:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to
        try:
            with smtplib.SMTP(settings["host"], settings["port"]) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(user, password)
                smtp.sendmail(user, to, msg.as_string())
            return {"success": True, "message": f"{to}으로 이메일을 발송했습니다."}
        except smtplib.SMTPAuthenticationError:
            return {"success": False, "message": "인증 실패: 이메일 계정 또는 비밀번호를 확인해주세요."}
        except smtplib.SMTPRecipientsRefused:
            return {"success": False, "message": f"수신자 주소가 유효하지 않습니다: {to}"}
        except smtplib.SMTPException as e:
            return {"success": False, "message": f"SMTP 오류: {str(e)}"}
        except OSError as e:
            return {"success": False, "message": f"네트워크 오류: {str(e)}"}

    logger.info(f"Sending email via {provider} to {to} (subject: {subject[:30]})")
    result = await asyncio.to_thread(_send)
    if result["success"]:
        logger.info(f"Email sent successfully via {provider} to {to}")
    else:
        logger.warning(f"Email send failed via {provider}: {result['message']}")
    return result


def _decode_header_value(value: str) -> str:
    """Decode MIME-encoded email header value."""
    parts = decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


async def check_new_mail(provider: str) -> list[dict]:
    """Check INBOX for unread mail via IMAP. Returns up to 10 recent unseen messages."""
    import src.config as config

    settings = IMAP_SETTINGS.get(provider)
    if settings is None:
        logger.warning(f"Unsupported IMAP provider: {provider}")
        return []

    if provider == "naver":
        user = config.EMAIL_NAVER_USER
        password = config.EMAIL_NAVER_PASSWORD
    else:
        user = config.EMAIL_GMAIL_USER
        password = config.EMAIL_GMAIL_PASSWORD

    if not user or not password:
        logger.warning(f"IMAP credentials not set for provider: {provider}")
        return []

    def _check() -> list[dict]:
        try:
            with imaplib.IMAP4_SSL(settings["host"], settings["port"]) as imap:
                imap.login(user, password)
                imap.select("INBOX")
                _, data = imap.search(None, "UNSEEN")
                mail_ids = data[0].split()
                if not mail_ids:
                    return []

                results = []
                for mail_id in mail_ids[-10:]:  # most recent 10
                    _, msg_data = imap.fetch(mail_id, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
                    raw = msg_data[0][1].decode("utf-8", errors="replace")
                    from_val = subject_val = date_val = ""
                    for line in raw.splitlines():
                        if line.lower().startswith("from:"):
                            from_val = _decode_header_value(line[5:].strip())
                        elif line.lower().startswith("subject:"):
                            subject_val = _decode_header_value(line[8:].strip())
                        elif line.lower().startswith("date:"):
                            date_val = line[5:].strip()
                    results.append({"from": from_val, "subject": subject_val, "date": date_val})
                return results
        except imaplib.IMAP4.error as e:
            logger.warning(f"IMAP error for {provider}: {e}")
            return []
        except OSError as e:
            logger.warning(f"Network error checking mail for {provider}: {e}")
            return []

    logger.info(f"Checking new mail via IMAP: provider={provider}")
    return await asyncio.to_thread(_check)
