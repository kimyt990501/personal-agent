"""Database operations for mail notification settings."""

import aiosqlite
from src.config import DB_PATH
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class MailDB:
    """Database operations for mail notification settings."""

    def __init__(self):
        self.db_path = DB_PATH

    async def get_settings(self, user_id: str) -> dict | None:
        """Get mail settings for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT enabled, last_checked FROM mail_settings WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
        if row:
            return {"enabled": bool(row[0]), "last_checked": row[1]}
        return None

    async def set_enabled(self, user_id: str, enabled: bool):
        """Enable or disable mail notifications for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO mail_settings (user_id, enabled)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET enabled = excluded.enabled
                """,
                (user_id, int(enabled))
            )
            await db.commit()

    async def update_last_checked(self, user_id: str, timestamp: str):
        """Update last_checked timestamp."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO mail_settings (user_id, last_checked)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET last_checked = excluded.last_checked
                """,
                (user_id, timestamp)
            )
            await db.commit()

    async def get_all_enabled(self) -> list[dict]:
        """Get all users with mail notifications enabled."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT user_id, last_checked FROM mail_settings WHERE enabled = 1"
            )
            rows = await cursor.fetchall()
        return [{"user_id": row[0], "last_checked": row[1]} for row in rows]
