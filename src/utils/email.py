"""SMTP email sending utility."""

import asyncio
import smtplib
from email.mime.text import MIMEText

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

SMTP_SETTINGS = {
    "gmail": {"host": "smtp.gmail.com", "port": 587},
    "naver": {"host": "smtp.naver.com", "port": 587},
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
