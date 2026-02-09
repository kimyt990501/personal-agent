import json
import os
from datetime import datetime
from pathlib import Path

from discord import Message

from src.llm.ollama_client import OllamaClient


ALLOWED_ROOT = "/Volumes/ssd"

DIRECT_COMMANDS = {"ls", "read", "find", "info"}

PARSE_PROMPT = """You are a filesystem command parser. The user wants to interact with files on their computer.
Allowed root path: {root}

Convert the user's natural language request into a JSON command.
Available commands:
- {{"action": "ls", "path": "<directory path>"}} - list directory contents
- {{"action": "read", "path": "<file path>"}} - read file contents
- {{"action": "find", "pattern": "<glob pattern>"}} - search for files
- {{"action": "info", "path": "<file/directory path>"}} - get file/directory info

Rules:
- All paths must start with {root}
- If the user mentions a relative path, prepend {root}
- "workspace" means {root}/workspace
- Reply with ONLY the JSON object, nothing else

User request: {query}"""


class FileSystemHandler:
    """Handler for filesystem access commands."""

    def __init__(self, ollama: OllamaClient):
        self.ollama = ollama

    async def handle(self, message: Message, content: str):
        """Handle filesystem command."""
        text = content[4:].strip()

        if not text:
            await message.reply(
                "사용법:\n"
                "`/fs ls <경로>` - 디렉터리 목록\n"
                "`/fs read <경로>` - 파일 읽기\n"
                "`/fs find <파일명>` - 파일 검색\n"
                "`/fs info <경로>` - 파일/폴더 정보\n\n"
                "자연어도 가능: `/fs 워크스페이스에 뭐 있어?`\n\n"
                f"허용 경로: `{ALLOWED_ROOT}`"
            )
            return

        parts = text.split(None, 1)
        sub_cmd = parts[0].lower()

        # Direct command mode
        if sub_cmd in DIRECT_COMMANDS:
            arg = parts[1] if len(parts) > 1 else ""
            await self._execute(message, sub_cmd, arg)
            return

        # Natural language mode
        await self._handle_natural(message, text)

    async def _handle_natural(self, message: Message, query: str):
        """Parse natural language and execute filesystem command."""
        async with message.channel.typing():
            try:
                prompt = PARSE_PROMPT.format(root=ALLOWED_ROOT, query=query)
                raw = await self.ollama.chat([{"role": "user", "content": prompt}])

                # Extract JSON from response
                raw = raw.strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

                cmd = json.loads(raw)
                action = cmd.get("action")

                if action == "ls":
                    result = await self._list_dir_result(cmd.get("path", ALLOWED_ROOT))
                elif action == "read":
                    result = await self._read_file_result(cmd.get("path", ""))
                elif action == "find":
                    result = await self._find_file_result(cmd.get("pattern", ""))
                elif action == "info":
                    result = await self._file_info_result(cmd.get("path", ""))
                else:
                    await message.reply("요청을 이해하지 못했어요. 다시 시도해주세요.")
                    return

                # Let LLM summarize the result naturally
                summary_prompt = (
                    f"사용자 요청: {query}\n\n"
                    f"파일시스템 조회 결과:\n{result}\n\n"
                    f"위 결과를 사용자에게 자연스럽게 답변해주세요. 간결하게."
                )
                response = await self.ollama.chat([{"role": "user", "content": summary_prompt}])
                await self._send_response(message, response)

            except (json.JSONDecodeError, KeyError):
                await message.reply("요청을 파싱하지 못했어요. 직접 명령어를 사용해보세요: `/fs`")
            except Exception as e:
                await message.reply(f"오류가 발생했습니다: {str(e)}")

    async def _execute(self, message: Message, action: str, arg: str):
        """Execute a direct command and send raw result."""
        if action == "ls":
            await self._list_dir(message, arg)
        elif action == "read":
            await self._read_file(message, arg)
        elif action == "find":
            await self._find_file(message, arg)
        elif action == "info":
            await self._file_info(message, arg)

    # --- Result methods (return string) for natural language mode ---

    async def _list_dir_result(self, arg: str) -> str:
        if not arg:
            arg = ALLOWED_ROOT
        path = self._validate_path(arg)
        if path is None:
            return f"접근 불가: 허용 경로는 {ALLOWED_ROOT} 입니다."
        if not path.is_dir():
            return "디렉터리가 아니거나 존재하지 않음"
        try:
            entries = sorted(path.iterdir())
            if not entries:
                return f"{path} - 비어 있음"
            lines = [f"디렉터리: {path}\n"]
            for e in entries[:50]:
                kind = "[DIR]" if e.is_dir() else "[FILE]"
                lines.append(f"{kind} {e.name}")
            if len(entries) > 50:
                lines.append(f"...외 {len(entries) - 50}개")
            return "\n".join(lines)
        except PermissionError:
            return "접근 권한 없음"

    async def _read_file_result(self, arg: str) -> str:
        if not arg:
            return "파일 경로가 필요합니다."
        path = self._validate_path(arg)
        if path is None:
            return f"접근 불가: 허용 경로는 {ALLOWED_ROOT} 입니다."
        if not path.is_file():
            return "파일이 아니거나 존재하지 않음"
        size = path.stat().st_size
        if size > 100_000:
            return f"파일이 너무 큼 ({self._format_size(size)}). 100KB 이하만 가능."
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            if len(text) > 3800:
                return text[:3800] + "\n...(이하 생략)"
            return text
        except Exception as e:
            return f"읽기 실패: {str(e)}"

    async def _find_file_result(self, pattern: str) -> str:
        if not pattern:
            return "검색 패턴이 필요합니다."
        root = Path(ALLOWED_ROOT)
        try:
            matches = list(root.rglob(pattern))[:20]
            if not matches:
                return f"{pattern} - 검색 결과 없음"
            lines = [f"검색: {pattern}\n"]
            for m in matches:
                kind = "[DIR]" if m.is_dir() else "[FILE]"
                lines.append(f"{kind} {m}")
            if len(matches) == 20:
                lines.append("...외 다수")
            return "\n".join(lines)
        except Exception as e:
            return f"검색 실패: {str(e)}"

    async def _file_info_result(self, arg: str) -> str:
        if not arg:
            return "경로가 필요합니다."
        path = self._validate_path(arg)
        if path is None:
            return f"접근 불가: 허용 경로는 {ALLOWED_ROOT} 입니다."
        if not path.exists():
            return "존재하지 않는 경로"
        stat = path.stat()
        file_type = "디렉터리" if path.is_dir() else "파일"
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        created = datetime.fromtimestamp(stat.st_birthtime).strftime("%Y-%m-%d %H:%M:%S")
        info = f"유형: {file_type}\n경로: {path}\n크기: {self._format_size(stat.st_size)}\n생성: {created}\n수정: {modified}"
        if path.is_dir():
            children = list(path.iterdir())
            dirs = sum(1 for c in children if c.is_dir())
            files = sum(1 for c in children if c.is_file())
            info += f"\n내용: 폴더 {dirs}개, 파일 {files}개"
        return info

    # --- Direct command methods (send message directly) ---

    def _validate_path(self, path_str: str) -> Path | None:
        try:
            path = Path(path_str).expanduser().resolve()
            if not str(path).startswith(ALLOWED_ROOT):
                return None
            return path
        except Exception:
            return None

    async def _list_dir(self, message: Message, arg: str):
        result = await self._list_dir_result(arg)
        # Format for direct display
        if not arg:
            arg = ALLOWED_ROOT
        path = self._validate_path(arg)
        if path is None or not path.is_dir():
            await message.reply(result)
            return
        try:
            entries = sorted(path.iterdir())
            if not entries:
                await message.reply(f"📂 `{path}` - 비어 있음")
                return
            lines = [f"📂 `{path}`\n"]
            for e in entries[:50]:
                icon = "📁" if e.is_dir() else "📄"
                lines.append(f"{icon} `{e.name}`")
            if len(entries) > 50:
                lines.append(f"\n...외 {len(entries) - 50}개")
            await self._send_response(message, "\n".join(lines))
        except PermissionError:
            await message.reply("접근 권한이 없어요.")

    async def _read_file(self, message: Message, arg: str):
        if not arg:
            await message.reply("파일 경로를 입력해주세요.")
            return
        path = self._validate_path(arg)
        if path is None:
            await message.reply(f"접근 불가: 허용 경로는 `{ALLOWED_ROOT}` 입니다.")
            return
        if not path.is_file():
            await message.reply("파일이 아니거나 존재하지 않아요.")
            return
        size = path.stat().st_size
        if size > 100_000:
            await message.reply(f"파일이 너무 커요 ({self._format_size(size)}). 100KB 이하만 읽을 수 있어요.")
            return
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            response = f"📄 `{path.name}`\n```\n{text[:3800]}\n```"
            if len(text) > 3800:
                response += f"\n...(이하 생략, 전체 {len(text)}자)"
            await self._send_response(message, response)
        except Exception as e:
            await message.reply(f"파일 읽기 실패: {str(e)}")

    async def _find_file(self, message: Message, arg: str):
        if not arg:
            await message.reply("검색할 파일명을 입력해주세요. 예: `/fs find *.pdf`")
            return
        root = Path(ALLOWED_ROOT)
        try:
            matches = list(root.rglob(arg))[:20]
            if not matches:
                await message.reply(f"🔍 `{arg}` - 검색 결과 없음")
                return
            lines = [f"🔍 `{arg}` 검색 결과:\n"]
            for m in matches:
                icon = "📁" if m.is_dir() else "📄"
                lines.append(f"{icon} `{m}`")
            if len(matches) == 20:
                lines.append(f"\n...외 다수")
            await self._send_response(message, "\n".join(lines))
        except Exception as e:
            await message.reply(f"검색 실패: {str(e)}")

    async def _file_info(self, message: Message, arg: str):
        if not arg:
            await message.reply("경로를 입력해주세요.")
            return
        path = self._validate_path(arg)
        if path is None:
            await message.reply(f"접근 불가: 허용 경로는 `{ALLOWED_ROOT}` 입니다.")
            return
        if not path.exists():
            await message.reply("존재하지 않는 경로예요.")
            return
        stat = path.stat()
        file_type = "디렉터리" if path.is_dir() else "파일"
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        created = datetime.fromtimestamp(stat.st_birthtime).strftime("%Y-%m-%d %H:%M:%S")
        info = (
            f"**{file_type} 정보**\n"
            f"• 경로: `{path}`\n"
            f"• 크기: {self._format_size(stat.st_size)}\n"
            f"• 생성: {created}\n"
            f"• 수정: {modified}"
        )
        if path.is_dir():
            children = list(path.iterdir())
            dirs = sum(1 for c in children if c.is_dir())
            files = sum(1 for c in children if c.is_file())
            info += f"\n• 내용: 폴더 {dirs}개, 파일 {files}개"
        await message.reply(info)

    def _format_size(self, size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"

    async def _send_response(self, message: Message, response: str):
        if len(response) > 2000:
            chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
            for chunk in chunks:
                await message.reply(chunk)
        else:
            await message.reply(response)
