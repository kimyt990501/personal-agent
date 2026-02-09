from discord import Message

from src.db import DB


class MemoHandler:
    """Handler for memo commands."""

    def __init__(self, db: DB):
        self.db = db

    async def handle(self, message: Message, user_id: str, content: str):
        """Handle memo commands."""
        parts = content.split(maxsplit=2)

        # /m alone
        if len(parts) == 1:
            await self._show_help(message)
            return

        cmd = parts[1].lower()

        if cmd == "list":
            await self._list_memos(message, user_id)
        elif cmd == "del":
            await self._delete_memo(message, user_id, parts)
        elif cmd == "find":
            await self._search_memos(message, user_id, parts)
        else:
            await self._save_memo(message, user_id, content)

    async def _show_help(self, message: Message):
        """Show memo help."""
        await message.reply(
            "**📝 메모 사용법**\n"
            "`/m <내용>` - 메모 저장\n"
            "`/m list` - 메모 목록\n"
            "`/m del <번호>` - 메모 삭제\n"
            "`/m find <검색어>` - 메모 검색"
        )

    async def _list_memos(self, message: Message, user_id: str):
        """List all memos."""
        memos = await self.db.memo.get_all(user_id)
        if not memos:
            await message.reply("저장된 메모가 없어요.")
            return

        memo_list = []
        for memo in memos:
            date = memo['created_at'][:10] if memo['created_at'] else ""
            preview = memo['content'][:50] + "..." if len(memo['content']) > 50 else memo['content']
            memo_list.append(f"`{memo['id']}` [{date}] {preview}")

        await message.reply("**📝 메모 목록**\n" + "\n".join(memo_list))

    async def _delete_memo(self, message: Message, user_id: str, parts: list):
        """Delete a memo."""
        if len(parts) < 3:
            await message.reply("삭제할 메모 번호를 입력해주세요. 예: `/m del 1`")
            return

        try:
            memo_id = int(parts[2])
            deleted = await self.db.memo.delete(user_id, memo_id)
            if deleted:
                await message.reply(f"메모 #{memo_id} 삭제 완료!")
            else:
                await message.reply(f"메모 #{memo_id}를 찾을 수 없어요.")
        except ValueError:
            await message.reply("올바른 메모 번호를 입력해주세요.")

    async def _search_memos(self, message: Message, user_id: str, parts: list):
        """Search memos."""
        if len(parts) < 3:
            await message.reply("검색어를 입력해주세요. 예: `/m find 장보기`")
            return

        query = parts[2]
        memos = await self.db.memo.search(user_id, query)
        if not memos:
            await message.reply(f"'{query}'에 대한 메모를 찾지 못했어요.")
            return

        memo_list = []
        for memo in memos:
            date = memo['created_at'][:10] if memo['created_at'] else ""
            preview = memo['content'][:50] + "..." if len(memo['content']) > 50 else memo['content']
            memo_list.append(f"`{memo['id']}` [{date}] {preview}")

        await message.reply(f"**🔍 '{query}' 검색 결과**\n" + "\n".join(memo_list))

    async def _save_memo(self, message: Message, user_id: str, content: str):
        """Save a new memo."""
        memo_content = content[3:].strip()  # Remove "/m "
        if memo_content:
            memo_id = await self.db.memo.add(user_id, memo_content)
            await message.reply(f"메모 저장 완료! (#{memo_id})")
        else:
            await message.reply("메모 내용을 입력해주세요.")
