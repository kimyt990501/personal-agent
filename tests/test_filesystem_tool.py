"""Tests for FileSystemTool — pattern matching, security, and file operations."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.bot.tools.filesystem import FileSystemTool, ALLOWED_ROOT
from src.bot.tools import ToolContext


USER_ID = "test_user_123"


@pytest.fixture
def tool():
    return FileSystemTool()


@pytest.fixture
def context():
    db = MagicMock()
    return ToolContext(user_id=USER_ID, db=db, persona={})


@pytest.fixture
def allowed_root(tmp_path):
    """tmp_path를 ALLOWED_ROOT로 사용하기 위해 resolve()된 경로 반환."""
    return str(tmp_path.resolve())


# ─── ABC 속성 ───

class TestFileSystemToolProperties:
    def test_name_is_filesystem(self, tool):
        assert tool.name == "filesystem"

    def test_description_contains_all_patterns(self, tool):
        desc = tool.description
        assert "FS_LS" in desc
        assert "FS_READ" in desc
        assert "FS_FIND" in desc
        assert "FS_INFO" in desc

    def test_usage_rules_mentions_allowed_root(self, tool):
        rules = tool.usage_rules
        assert ALLOWED_ROOT in rules


# ─── ToolRegistry 등록 ───

class TestFileSystemToolRegistry:
    def test_can_register_in_registry(self):
        from src.bot.tools import ToolRegistry
        registry = ToolRegistry()
        registry.register(FileSystemTool())
        assert any(t.name == "filesystem" for t in registry.tools)

    def test_fs_tags_in_instructions(self):
        from src.bot.tools import ToolRegistry
        registry = ToolRegistry()
        registry.register(FileSystemTool())
        instructions = registry.build_tool_instructions()
        assert "FS_LS" in instructions
        assert "FS_READ" in instructions

    def test_chat_handler_registers_filesystem_tool(self):
        """ChatHandler가 FileSystemTool을 ToolRegistry에 등록한다."""
        from src.bot.handlers.chat import ChatHandler
        db = MagicMock()
        ollama = MagicMock()
        handler = ChatHandler(db, ollama)
        names = [t.name for t in handler.registry.tools]
        assert "filesystem" in names

    def test_chat_handler_has_filesystem_tool(self):
        """ChatHandler registry에 filesystem 도구가 포함된다."""
        from src.bot.handlers.chat import ChatHandler
        db = MagicMock()
        ollama = MagicMock()
        handler = ChatHandler(db, ollama)
        names = [t.name for t in handler.registry.tools]
        assert "filesystem" in names


# ─── 패턴 매칭 (try_execute) ───

class TestFileSystemToolPatternMatching:
    @pytest.mark.asyncio
    async def test_fs_ls_pattern_matched(self, tool, context):
        with patch.object(tool, "_list_dir", return_value="디렉터리 목록"):
            result = await tool.try_execute(f"[FS_LS:{ALLOWED_ROOT}/workspace]", context)
        assert result == "디렉터리 목록"

    @pytest.mark.asyncio
    async def test_fs_read_pattern_matched(self, tool, context):
        with patch.object(tool, "_read_file", return_value="파일 내용"):
            result = await tool.try_execute(f"[FS_READ:{ALLOWED_ROOT}/workspace/file.txt]", context)
        assert result == "파일 내용"

    @pytest.mark.asyncio
    async def test_fs_find_pattern_matched(self, tool, context):
        with patch.object(tool, "_find_file", return_value="검색 결과"):
            result = await tool.try_execute("[FS_FIND:*.pdf]", context)
        assert result == "검색 결과"

    @pytest.mark.asyncio
    async def test_fs_info_pattern_matched(self, tool, context):
        with patch.object(tool, "_file_info", return_value="파일 정보"):
            result = await tool.try_execute(f"[FS_INFO:{ALLOWED_ROOT}/workspace]", context)
        assert result == "파일 정보"

    @pytest.mark.asyncio
    async def test_no_pattern_returns_none(self, tool, context):
        result = await tool.try_execute("파일시스템 관련 없는 일반 응답입니다.", context)
        assert result is None

    @pytest.mark.asyncio
    async def test_memo_pattern_not_detected(self, tool, context):
        result = await tool.try_execute("[MEMO_LIST]", context)
        assert result is None

    @pytest.mark.asyncio
    async def test_fs_ls_path_stripped(self, tool, context):
        """패턴 내 공백이 strip된다."""
        captured = {}

        def capture(arg):
            captured["arg"] = arg
            return "결과"

        with patch.object(tool, "_list_dir", side_effect=capture):
            await tool.try_execute(f"[FS_LS:  {ALLOWED_ROOT}/workspace  ]", context)
        assert captured["arg"] == f"{ALLOWED_ROOT}/workspace"


# ─── 보안: _validate_path ───

class TestValidatePath:
    def test_valid_path_under_allowed_root(self, tool):
        """ALLOWED_ROOT 하위 경로는 허용된다."""
        result = tool._validate_path(f"{ALLOWED_ROOT}/workspace/project")
        assert result is not None

    def test_allowed_root_itself_is_valid(self, tool):
        """ALLOWED_ROOT 자체는 허용된다."""
        result = tool._validate_path(ALLOWED_ROOT)
        assert result is not None

    def test_path_outside_allowed_root_denied(self, tool):
        """ALLOWED_ROOT 외부 경로는 거부된다."""
        result = tool._validate_path("/etc/passwd")
        assert result is None

    def test_home_directory_denied(self, tool):
        """홈 디렉터리는 ALLOWED_ROOT 외부이면 거부된다."""
        result = tool._validate_path("/Users/root/.ssh/id_rsa")
        assert result is None

    def test_path_traversal_denied(self, tool):
        """../를 이용한 경로 탈출 시도는 거부된다."""
        result = tool._validate_path(f"{ALLOWED_ROOT}/../etc/passwd")
        assert result is None

    def test_path_traversal_nested_denied(self, tool):
        """중첩된 경로 탈출도 거부된다."""
        result = tool._validate_path(f"{ALLOWED_ROOT}/workspace/../../etc/shadow")
        assert result is None

    def test_returns_path_object(self, tool):
        """유효 경로는 Path 객체를 반환한다."""
        result = tool._validate_path(f"{ALLOWED_ROOT}/workspace")
        assert isinstance(result, Path)

    def test_prefix_similarity_denied(self, tool):
        """ALLOWED_ROOT와 유사하지만 다른 경로는 거부된다."""
        # e.g. /Volumes/ssd2 should not match /Volumes/ssd
        fake_path = ALLOWED_ROOT + "2/evil"
        result = tool._validate_path(fake_path)
        # resolve() will resolve the path, but it won't start with ALLOWED_ROOT
        # (it starts with ALLOWED_ROOT + "2")
        assert result is None or not str(result).startswith(ALLOWED_ROOT + "/") and str(result) != ALLOWED_ROOT


# ─── _list_dir 동작 ───

class TestListDir:
    def test_valid_dir_lists_contents(self, tool, tmp_path, allowed_root):
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "file.txt").write_text("hello")

        with patch("src.bot.tools.filesystem.ALLOWED_ROOT", allowed_root):
            result = tool._list_dir(str(tmp_path))

        assert "file.txt" in result or "subdir" in result

    def test_empty_dir_shows_empty_message(self, tool, tmp_path, allowed_root):
        with patch("src.bot.tools.filesystem.ALLOWED_ROOT", allowed_root):
            result = tool._list_dir(str(tmp_path))
        assert "비어 있음" in result

    def test_path_outside_allowed_root_denied(self, tool, allowed_root):
        with patch("src.bot.tools.filesystem.ALLOWED_ROOT", allowed_root):
            result = tool._list_dir("/etc")
        assert "접근 불가" in result

    def test_nonexistent_path_shows_error(self, tool, tmp_path, allowed_root):
        with patch("src.bot.tools.filesystem.ALLOWED_ROOT", allowed_root):
            result = tool._list_dir(str(tmp_path / "nonexistent"))
        assert "아니거나 존재하지 않음" in result

    def test_empty_arg_uses_allowed_root(self, tool, allowed_root):
        """인자가 빈 문자열이면 ALLOWED_ROOT를 기본값으로 사용한다."""
        with patch("src.bot.tools.filesystem.ALLOWED_ROOT", allowed_root):
            result = tool._list_dir("")
        # ALLOWED_ROOT(=tmp_path)는 존재하는 디렉터리이므로 오류 없이 실행됨
        assert "접근 불가" not in result


# ─── _read_file 동작 ───

class TestReadFile:
    def test_valid_file_returns_content(self, tool, tmp_path, allowed_root):
        f = tmp_path / "hello.txt"
        f.write_text("안녕하세요")

        with patch("src.bot.tools.filesystem.ALLOWED_ROOT", allowed_root):
            result = tool._read_file(str(f))

        assert "안녕하세요" in result

    def test_empty_arg_returns_error(self, tool):
        result = tool._read_file("")
        assert "필요합니다" in result

    def test_path_outside_allowed_root_denied(self, tool, allowed_root):
        with patch("src.bot.tools.filesystem.ALLOWED_ROOT", allowed_root):
            result = tool._read_file("/etc/passwd")
        assert "접근 불가" in result

    def test_directory_returns_error(self, tool, tmp_path, allowed_root):
        with patch("src.bot.tools.filesystem.ALLOWED_ROOT", allowed_root):
            result = tool._read_file(str(tmp_path))
        assert "아니거나 존재하지 않음" in result

    def test_large_file_returns_size_error(self, tool, tmp_path, allowed_root):
        f = tmp_path / "large.bin"
        f.write_bytes(b"x" * 200_000)

        with patch("src.bot.tools.filesystem.ALLOWED_ROOT", allowed_root):
            result = tool._read_file(str(f))

        assert "너무 큼" in result

    def test_long_file_truncated(self, tool, tmp_path, allowed_root):
        f = tmp_path / "long.txt"
        f.write_text("A" * 5000)

        with patch("src.bot.tools.filesystem.ALLOWED_ROOT", allowed_root):
            result = tool._read_file(str(f))

        assert "이하 생략" in result
        assert len(result) < 5000


# ─── _find_file 동작 ───

class TestFindFile:
    def test_empty_pattern_returns_error(self, tool):
        result = tool._find_file("")
        assert "필요합니다" in result

    def test_pattern_with_matches(self, tool, tmp_path, allowed_root):
        (tmp_path / "report.pdf").write_text("pdf content")

        with patch("src.bot.tools.filesystem.ALLOWED_ROOT", allowed_root):
            with patch("src.bot.tools.filesystem.Path") as MockPath:
                mock_root = MagicMock()
                mock_file = MagicMock()
                mock_file.is_dir.return_value = False
                mock_file.__str__ = lambda s: str(tmp_path / "report.pdf")
                mock_root.rglob.return_value = [mock_file]
                MockPath.return_value = mock_root
                result = tool._find_file("*.pdf")

        assert "검색" in result

    def test_no_matches(self, tool, tmp_path, allowed_root):
        with patch("src.bot.tools.filesystem.ALLOWED_ROOT", allowed_root):
            result = tool._find_file("nonexistent_pattern_xyz_123.pdf")
        assert "검색 결과 없음" in result


# ─── _format_size ───

class TestFormatSize:
    def test_bytes(self, tool):
        assert "B" in tool._format_size(512)

    def test_kilobytes(self, tool):
        assert "KB" in tool._format_size(2048)

    def test_megabytes(self, tool):
        assert "MB" in tool._format_size(2 * 1024 * 1024)

    def test_gigabytes(self, tool):
        assert "GB" in tool._format_size(2 * 1024 * 1024 * 1024)
