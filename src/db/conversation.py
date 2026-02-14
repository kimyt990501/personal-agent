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
