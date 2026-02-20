import re
from datetime import datetime
from pathlib import Path

from src.bot.tools.base import Tool, ToolContext
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ALLOWED_ROOT = "/Volumes/ssd"

FS_LS_PATTERN = re.compile(r"\[FS_LS:([^\]]+)\]")
FS_READ_PATTERN = re.compile(r"\[FS_READ:([^\]]+)\]")
FS_FIND_PATTERN = re.compile(r"\[FS_FIND:([^\]]+)\]")
FS_INFO_PATTERN = re.compile(r"\[FS_INFO:([^\]]+)\]")


class FileSystemTool(Tool):

    @property
    def name(self) -> str:
        return "filesystem"

    @property
    def description(self) -> str:
        return (
            "- FileSystem: When the user wants to browse, read, search, or inspect files/directories, use these tags:\n"
            f"  - [FS_LS:<path>] - List directory contents (e.g. [FS_LS:/Volumes/ssd/workspace])\n"
            "  - [FS_READ:<path>] - Read file contents (e.g. [FS_READ:/Volumes/ssd/workspace/project/config.py])\n"
            "  - [FS_FIND:<pattern>] - Search files by glob pattern (e.g. [FS_FIND:*.pdf], [FS_FIND:config.py])\n"
            "  - [FS_INFO:<path>] - Get file or directory metadata (e.g. [FS_INFO:/Volumes/ssd/workspace/bot.log])"
        )

    @property
    def usage_rules(self) -> str:
        return (
            f"- For filesystem, detect when the user asks about files or directories "
            f"(\"파일 뭐 있어?\", \"폴더 보여줘\", \"읽어줘\", \"찾아줘\", \"정보 알려줘\"). "
            f"All paths must start with {ALLOWED_ROOT}. "
            f"If the user says 'workspace', use {ALLOWED_ROOT}/workspace. "
            f"Never access paths outside {ALLOWED_ROOT}."
        )

    def _validate_path(self, path_str: str) -> Path | None:
        try:
            path = Path(path_str).expanduser().resolve()
            if not str(path).startswith(ALLOWED_ROOT):
                return None
            return path
        except Exception:
            return None

    def _format_size(self, size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"

    def _list_dir(self, arg: str) -> str:
        path = self._validate_path(arg) if arg else Path(ALLOWED_ROOT)
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

    def _read_file(self, arg: str) -> str:
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

    def _find_file(self, pattern: str) -> str:
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

    def _file_info(self, arg: str) -> str:
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
        info = (
            f"유형: {file_type}\n"
            f"경로: {path}\n"
            f"크기: {self._format_size(stat.st_size)}\n"
            f"생성: {created}\n"
            f"수정: {modified}"
        )
        if path.is_dir():
            children = list(path.iterdir())
            dirs = sum(1 for c in children if c.is_dir())
            files = sum(1 for c in children if c.is_file())
            info += f"\n내용: 폴더 {dirs}개, 파일 {files}개"
        return info

    async def try_execute(self, response: str, context: ToolContext) -> str | None:
        # Try FS_LS
        match = FS_LS_PATTERN.search(response)
        if match:
            path_arg = match.group(1).strip()
            logger.info(f"Tool called: [FS_LS:{path_arg}]")
            return self._list_dir(path_arg)

        # Try FS_READ
        match = FS_READ_PATTERN.search(response)
        if match:
            path_arg = match.group(1).strip()
            logger.info(f"Tool called: [FS_READ:{path_arg}]")
            return self._read_file(path_arg)

        # Try FS_FIND
        match = FS_FIND_PATTERN.search(response)
        if match:
            pattern = match.group(1).strip()
            logger.info(f"Tool called: [FS_FIND:{pattern}]")
            return self._find_file(pattern)

        # Try FS_INFO
        match = FS_INFO_PATTERN.search(response)
        if match:
            path_arg = match.group(1).strip()
            logger.info(f"Tool called: [FS_INFO:{path_arg}]")
            return self._file_info(path_arg)

        return None
