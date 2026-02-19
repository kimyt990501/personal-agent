from discord import Message

from src.db import DB
from src.llm.ollama_client import OllamaClient
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class CommandHandler:
    """Handler for basic bot commands."""

    def __init__(self, db: DB, ollama: OllamaClient):
        self.db = db
        self.ollama = ollama

    async def handle_help(self, message: Message):
        """Show help message."""
        help_text = (
            "**📚 명령어 목록**\n\n"
            "`/cmd` - 이 도움말 보기\n"
            "`/ping` - Ollama 연결 상태 확인\n"
            "`/persona` - 현재 페르소나 확인\n"
            "`/clear` - 대화 기록 초기화 (페르소나 유지)\n"
            "`/newme` - 페르소나 + 대화 기록 전부 초기화\n"
            "`/s <검색어>` - 웹 검색 후 AI가 답변\n\n"
            "**📝 메모**\n"
            "`/m <내용>` - 메모 저장\n"
            "`/m list` - 메모 목록 보기\n"
            "`/m del <번호>` - 메모 삭제\n"
            "`/m find <검색어>` - 메모 검색\n\n"
            "**⏰ 리마인더**\n"
            "`/r <시간> <내용>` - 1회 리마인더\n"
            "`/r daily <시간> <내용>` - 매일 반복\n"
            "`/r weekday <시간> <내용>` - 평일 반복\n"
            "`/r weekly <요일> <시간> <내용>` - 매주 반복\n"
            "`/r list` - 목록 / `/r del <번호>` - 삭제\n\n"
            "**🎲 랜덤 뽑기**\n"
            "`/pick <항목1> <항목2> ...` - 랜덤 선택\n"
            "예: `/pick 짜장 짬뽕 볶음밥`\n\n"
            "**💱 환율**\n"
            "`/ex <금액> <from> <to>` - 환율 변환\n"
            "예: `/ex 100 USD KRW`, `/ex JPY KRW`\n\n"
            "**🌐 번역**\n"
            "`/t <언어코드> <내용>` - 번역 (예: `/t en 안녕하세요`)\n"
            "지원: en, ko, ja, zh, es, fr, de\n\n"
            "**🌤️ 날씨**\n"
            "`/w <도시>` - 날씨 확인 (예: `/w 서울`)\n\n"
            "**📂 파일시스템**\n"
            "`/fs ls <경로>` - 디렉터리 목록\n"
            "`/fs read <경로>` - 파일 읽기\n"
            "`/fs find <파일명>` - 파일 검색\n"
            "`/fs info <경로>` - 파일/폴더 정보\n"
            "자연어: `/fs 워크스페이스에 뭐 있어?`\n\n"
            "**💡 사용법**\n"
            "• 일반 메시지를 보내면 AI가 응답해요\n"
            "• URL을 포함하면 자동으로 내용을 읽고 분석해요\n"
            "• 파일(PDF, 텍스트, 코드)을 첨부하면 분석해요"
        )
        await message.reply(help_text)

    async def handle_ping(self, message: Message):
        """Check Ollama connection status."""
        healthy = await self.ollama.check_health()
        status = "정상" if healthy else "연결 실패"
        await message.reply(f"Ollama 상태: {status}")

    async def handle_clear(self, message: Message, user_id: str):
        """Clear conversation history."""
        await self.db.conversation.clear_history(user_id)
        await self.db.conversation.clear_summary(user_id)
        await message.reply("대화 기록을 초기화했습니다.")

    async def handle_newme(self, message: Message, user_id: str, persona_setup: dict):
        """Clear everything and restart."""
        await self.db.conversation.clear_history(user_id)
        await self.db.conversation.clear_summary(user_id)
        await self.db.persona.clear(user_id)
        persona_setup.pop(user_id, None)
        await message.reply("대화 기록과 페르소나가 초기화되었습니다. 새로 시작해주세요!")

    async def handle_persona_info(self, message: Message, user_id: str):
        """Show current persona info."""
        persona = await self.db.persona.get(user_id)
        if persona:
            await message.reply(
                f"**현재 페르소나**\n"
                f"• 이름: {persona['name']}\n"
                f"• 역할: {persona['role']}\n"
                f"• 말투: {persona['tone']}\n\n"
                f"`/newme`로 초기화할 수 있어요."
            )
        else:
            await message.reply("설정된 페르소나가 없어요. 메시지를 보내면 설정을 시작합니다!")
