import io

from discord import Attachment, Message
from pypdf import PdfReader

from src.llm.ollama_client import OllamaClient


TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx",
    ".java", ".c", ".cpp", ".h", ".go", ".rs", ".rb",
    ".html", ".css", ".json", ".yaml", ".yml", ".toml",
    ".xml", ".csv", ".sql", ".sh", ".bat", ".log",
}

MAX_CONTENT_LENGTH = 8000


class FileHandler:
    """Handler for file attachment processing."""

    def __init__(self, ollama: OllamaClient):
        self.ollama = ollama

    async def handle(self, message: Message, user_message: str):
        """Handle message with file attachments."""
        attachment = message.attachments[0]
        filename = attachment.filename.lower()

        async with message.channel.typing():
            try:
                content = await self._extract_content(attachment, filename)
                if content is None:
                    await message.reply(
                        f"지원하지 않는 파일 형식이에요.\n"
                        f"지원: PDF, 텍스트/코드 파일"
                    )
                    return

                if not content.strip():
                    await message.reply("파일에서 내용을 추출하지 못했어요.")
                    return

                if len(content) > MAX_CONTENT_LENGTH:
                    content = content[:MAX_CONTENT_LENGTH] + "\n...(이하 생략)"

                instruction = user_message if user_message else "이 파일의 내용을 분석하고 요약해주세요."

                prompt = (
                    f"사용자가 파일을 첨부했습니다.\n"
                    f"파일명: {attachment.filename}\n\n"
                    f"**파일 내용:**\n{content}\n\n"
                    f"**사용자 요청:** {instruction}"
                )

                response = await self.ollama.chat(
                    [{"role": "user", "content": prompt}]
                )
                await self._send_response(message, response)

            except Exception as e:
                await message.reply(f"파일 처리 중 오류가 발생했습니다: {str(e)}")

    async def _extract_content(self, attachment: Attachment, filename: str) -> str | None:
        """Extract text content from attachment."""
        if filename.endswith(".pdf"):
            return await self._extract_pdf(attachment)

        ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
        if ext in TEXT_EXTENSIONS:
            data = await attachment.read()
            return data.decode("utf-8", errors="replace")

        return None

    async def _extract_pdf(self, attachment: Attachment) -> str:
        """Extract text from PDF attachment."""
        data = await attachment.read()
        reader = PdfReader(io.BytesIO(data))

        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages.append(f"[Page {i + 1}]\n{text}")

        return "\n\n".join(pages)

    async def _send_response(self, message: Message, response: str):
        """Send response, splitting if necessary."""
        if len(response) > 2000:
            chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
            for chunk in chunks:
                await message.reply(chunk)
        else:
            await message.reply(response)
