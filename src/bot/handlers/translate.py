from discord import Message

from src.llm.ollama_client import OllamaClient


LANG_MAP = {
    "en": "English",
    "ko": "한국어",
    "ja": "日本語",
    "zh": "中文",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
}


class TranslateHandler:
    """Handler for translation commands."""

    def __init__(self, ollama: OllamaClient):
        self.ollama = ollama

    async def handle(self, message: Message, content: str):
        """Handle translation command."""
        parts = content[3:].strip().split(None, 1)

        if len(parts) < 2:
            await message.reply(
                "사용법: `/t <언어코드> <내용>`\n"
                "예: `/t en 안녕하세요`\n\n"
                "**지원 언어코드:** " + ", ".join(f"`{k}` ({v})" for k, v in LANG_MAP.items())
            )
            return

        lang_code = parts[0].lower()
        text = parts[1]

        target_lang = LANG_MAP.get(lang_code, lang_code)

        async with message.channel.typing():
            prompt = (
                f"Translate the following text to {target_lang}. "
                f"Reply with ONLY the translated text, nothing else.\n\n"
                f"{text}"
            )

            try:
                response = await self.ollama.chat(
                    [{"role": "user", "content": prompt}]
                )
                await self._send_response(message, response)
            except Exception as e:
                await message.reply(f"번역 중 오류가 발생했습니다: {str(e)}")

    async def _send_response(self, message: Message, response: str):
        """Send response, splitting if necessary."""
        if len(response) > 2000:
            chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
            for chunk in chunks:
                await message.reply(chunk)
        else:
            await message.reply(response)