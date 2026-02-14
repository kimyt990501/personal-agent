import aiosqlite
from src.config import DB_PATH
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class MemoDB:
    """Database operations for memos."""

    def __init__(self):
        self.db_path = DB_PATH

    async def add(self, user_id: str, content: str) -> int:
        """Add a memo and return its ID."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO memos (user_id, content) VALUES (?, ?)",
                (user_id, content)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_all(self, user_id: str, limit: int = 20) -> list[dict]:
        """Get memos for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, content, created_at FROM memos
                WHERE user_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (user_id, limit)
            )
            rows = await cursor.fetchall()

        return [{"id": row[0], "content": row[1], "created_at": row[2]} for row in rows]

    async def delete(self, user_id: str, memo_id: int) -> bool:
        """Delete a memo. Returns True if deleted."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM memos WHERE id = ? AND user_id = ?",
                (memo_id, user_id)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def search(self, user_id: str, query: str) -> list[dict]:
        """Search memos by content."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, content, created_at FROM memos
                WHERE user_id = ? AND content LIKE ?
                ORDER BY created_at DESC, id DESC
                """,
                (user_id, f"%{query}%")
            )
            rows = await cursor.fetchall()

        return [{"id": row[0], "content": row[1], "created_at": row[2]} for row in rows]
