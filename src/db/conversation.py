import aiosqlite
from src.config import DB_PATH, MAX_HISTORY_LENGTH
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ConversationDB:
    """Database operations for conversation history."""

    def __init__(self):
        self.db_path = DB_PATH

    async def add_message(self, user_id: str, role: str, content: str):
        """Add a message to the conversation history."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)",
                (user_id, role, content)
            )
            await db.commit()

    async def get_history(self, user_id: str, limit: int = MAX_HISTORY_LENGTH) -> list[dict]:
        """Get conversation history for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT role, content FROM conversations
                WHERE user_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (user_id, limit)
            )
            rows = await cursor.fetchall()

        return [{"role": row[0], "content": row[1]} for row in reversed(rows)]

    async def clear_history(self, user_id: str):
        """Clear conversation history for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM conversations WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()

    async def get_message_count(self, user_id: str) -> int:
        """Get total message count for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM conversations WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
        return row[0] if row else 0

    async def get_all_messages(self, user_id: str) -> list[dict]:
        """Get all messages for a user in chronological order (no limit)."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT role, content FROM conversations
                WHERE user_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (user_id,)
            )
            rows = await cursor.fetchall()
        return [{"role": row[0], "content": row[1]} for row in rows]

    async def delete_old_messages(self, user_id: str, keep_count: int):
        """Delete old messages, keeping only the most recent keep_count messages."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                DELETE FROM conversations
                WHERE user_id = ? AND id NOT IN (
                    SELECT id FROM conversations
                    WHERE user_id = ?
                    ORDER BY created_at DESC, id DESC
                    LIMIT ?
                )
                """,
                (user_id, user_id, keep_count)
            )
            await db.commit()

    async def get_summary(self, user_id: str) -> str | None:
        """Get conversation summary for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT summary FROM conversation_summaries WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
        return row[0] if row else None

    async def save_summary(self, user_id: str, summary: str, message_count: int):
        """Save or update conversation summary, accumulating message_count."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO conversation_summaries (user_id, summary, message_count, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    summary = excluded.summary,
                    message_count = message_count + excluded.message_count,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, summary, message_count)
            )
            await db.commit()

    async def clear_summary(self, user_id: str):
        """Clear conversation summary for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM conversation_summaries WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()
