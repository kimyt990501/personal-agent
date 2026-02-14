"""Database operations for daily briefing settings."""

import aiosqlite
from src.config import DB_PATH
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class BriefingDB:
    """Database operations for briefing settings."""

    def __init__(self):
        self.db_path = DB_PATH

    async def get_settings(self, user_id: str) -> dict | None:
        """Get briefing settings for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT enabled, time, city, last_sent FROM briefing_settings
                WHERE user_id = ?
                """,
                (user_id,)
            )
            row = await cursor.fetchone()

        if row:
            return {
                "enabled": bool(row[0]),
                "time": row[1],
                "city": row[2],
                "last_sent": row[3]
            }
        return None

    async def set_settings(self, user_id: str, **kwargs):
        """Update briefing settings. Creates if not exists."""
        # Get current settings or use defaults
        current = await self.get_settings(user_id)
        if current is None:
            current = {
                "enabled": True,
                "time": "08:00",
                "city": "서울",
                "last_sent": None
            }

        # Update with provided kwargs
        current.update(kwargs)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO briefing_settings
                (user_id, enabled, time, city, last_sent)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, int(current["enabled"]), current["time"],
                 current["city"], current.get("last_sent"))
            )
            await db.commit()

    async def update_last_sent(self, user_id: str, last_sent: str):
        """Update the last_sent timestamp."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE briefing_settings SET last_sent = ? WHERE user_id = ?",
                (last_sent, user_id)
            )
            await db.commit()

    async def get_all_enabled(self) -> list[dict]:
        """Get all users with briefing enabled."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT user_id, time, city, last_sent FROM briefing_settings
                WHERE enabled = 1
                """
            )
            rows = await cursor.fetchall()

        return [{
            "user_id": row[0],
            "time": row[1],
            "city": row[2],
            "last_sent": row[3]
        } for row in rows]
