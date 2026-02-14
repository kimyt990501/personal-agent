import aiosqlite
from src.config import DB_PATH
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class PersonaDB:
    """Database operations for user personas."""

    def __init__(self):
        self.db_path = DB_PATH

    async def get(self, user_id: str) -> dict | None:
        """Get persona for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT name, role, tone FROM personas WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()

        if row:
            return {"name": row[0], "role": row[1], "tone": row[2]}
        return None

    async def set(self, user_id: str, name: str, role: str, tone: str):
        """Set or update persona for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO personas (user_id, name, role, tone)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    name = excluded.name,
                    role = excluded.role,
                    tone = excluded.tone
                """,
                (user_id, name, role, tone)
            )
            await db.commit()

    async def clear(self, user_id: str):
        """Clear persona for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM personas WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()
