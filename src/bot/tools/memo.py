import re

from src.bot.tools.base import Tool, ToolContext
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class MemoTool(Tool):
    MEMO_SAVE_PATTERN = re.compile(r"\[MEMO_SAVE:(.+)\]")
    MEMO_LIST_PATTERN = re.compile(r"\[MEMO_LIST\]")
    MEMO_SEARCH_PATTERN = re.compile(r"\[MEMO_SEARCH:(.+)\]")
    MEMO_DEL_PATTERN = re.compile(r"\[MEMO_DEL:(\d+)\]")

    @property
    def name(self) -> str:
        return "memo"

    @property
    def description(self) -> str:
        return (
            "- Memo: When the user wants to save, list, search, or delete memos, use these tags:\n"
            "  - [MEMO_SAVE:content] - Save a new memo (e.g. [MEMO_SAVE:우유 사기], [MEMO_SAVE:프로젝트 마감일 금요일])\n"
            "  - [MEMO_LIST] - List all saved memos\n"
            "  - [MEMO_SEARCH:keyword] - Search memos containing the keyword (e.g. [MEMO_SEARCH:우유], [MEMO_SEARCH:회의])\n"
            "  - [MEMO_DEL:position] - Delete a memo by position in the list (e.g. [MEMO_DEL:1] for first, [MEMO_DEL:2] for second)\n"
            "    IMPORTANT: Use the position number (1st, 2nd, 3rd...) from the list, NOT the database ID"
        )

    @property
    def usage_rules(self) -> str:
        return (
            "- For memo, detect when the user wants to save information for later "
            "(\"메모해줘\", \"기억해줘\", \"저장해줘\"), list memos (\"메모 뭐 있었지\", \"메모 목록\"), "
            "search (\"메모 찾아줘\", \"~에 대한 메모\"), or delete (\"메모 삭제\", \"메모 지워줘\", "
            "\"첫 번째 메모 삭제\"). When deleting, extract the position number (1st=1, 2nd=2, 3rd=3, etc.)."
        )

    async def try_execute(self, response: str, context: ToolContext) -> str | None:
        # Try MEMO_SAVE
        match = self.MEMO_SAVE_PATTERN.search(response)
        if match:
            content = match.group(1).strip()
            logger.info(f"Tool called: [MEMO_SAVE:{content[:50]}...]")
            memo_id = await context.db.memo.add(context.user_id, content)
            return f"메모 저장 완료:\n- ID: #{memo_id}\n- 내용: {content}"

        # Try MEMO_LIST
        match = self.MEMO_LIST_PATTERN.search(response)
        if match:
            logger.info("Tool called: [MEMO_LIST]")
            memos = await context.db.memo.get_all(context.user_id, limit=20)
            if not memos:
                return "저장된 메모가 없습니다."

            lines = ["저장된 메모 목록:"]
            for memo in memos:
                lines.append(f"- #{memo['id']}: {memo['content']} (작성: {memo['created_at']})")
            return "\n".join(lines)

        # Try MEMO_SEARCH
        match = self.MEMO_SEARCH_PATTERN.search(response)
        if match:
            query = match.group(1).strip()
            logger.info(f"Tool called: [MEMO_SEARCH:{query}]")
            memos = await context.db.memo.search(context.user_id, query)
            if not memos:
                return f"'{query}' 검색 결과가 없습니다."

            lines = [f"'{query}' 검색 결과:"]
            for memo in memos:
                lines.append(f"- #{memo['id']}: {memo['content']} (작성: {memo['created_at']})")
            return "\n".join(lines)

        # Try MEMO_DEL
        match = self.MEMO_DEL_PATTERN.search(response)
        if match:
            position = int(match.group(1))  # 사용자가 말한 "N번째" (1부터 시작)
            logger.info(f"Tool called: [MEMO_DEL:{position}]")

            # 순서 → 실제 DB ID 변환
            memos = await context.db.memo.get_all(context.user_id, limit=20)
            if position < 1 or position > len(memos):
                return f"메모가 {len(memos)}개만 있습니다. {position}번째 메모를 찾을 수 없습니다."

            # memos는 최신순 정렬이므로 position-1 인덱스가 해당 메모
            target_memo = memos[position - 1]
            actual_id = target_memo['id']

            deleted = await context.db.memo.delete(context.user_id, actual_id)
            if deleted:
                return f"메모 삭제 완료:\n- #{actual_id}: {target_memo['content']}"
            else:
                return f"메모 #{actual_id}를 찾을 수 없습니다."

        return None
