from datetime import datetime, timedelta

import aiosqlite
from src.config import DB_PATH


RECURRENCE_LABELS = {
    "daily": "매일",
    "weekday": "평일",
}


class ReminderDB:
    """Database operations for reminders."""

    def __init__(self):
        self.db_path = DB_PATH

    async def add(self, user_id: str, content: str, remind_at: str, recurrence: str | None = None) -> int:
        """Add a reminder and return its ID."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO reminders (user_id, content, remind_at, recurrence) VALUES (?, ?, ?, ?)",
                (user_id, content, remind_at, recurrence)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_all(self, user_id: str) -> list[dict]:
        """Get active reminders for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, content, remind_at, recurrence FROM reminders
                WHERE user_id = ?
                ORDER BY remind_at ASC
                """,
                (user_id,)
            )
            rows = await cursor.fetchall()

        return [
            {"id": row[0], "content": row[1], "remind_at": row[2], "recurrence": row[3]}
            for row in rows
        ]

    async def get_due(self) -> list[dict]:
        """Get all reminders that are due now."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, user_id, content, remind_at, recurrence FROM reminders
                WHERE remind_at <= datetime('now', 'localtime')
                """
            )
            rows = await cursor.fetchall()

        return [
            {"id": row[0], "user_id": row[1], "content": row[2], "remind_at": row[3], "recurrence": row[4]}
            for row in rows
        ]

    async def reschedule(self, reminder_id: int, next_remind_at: str):
        """Reschedule a recurring reminder to the next occurrence."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE reminders SET remind_at = ? WHERE id = ?",
                (next_remind_at, reminder_id)
            )
            await db.commit()

    async def delete(self, user_id: str, reminder_id: int) -> bool:
        """Delete a reminder. Returns True if deleted."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM reminders WHERE id = ? AND user_id = ?",
                (reminder_id, user_id)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def delete_by_id(self, reminder_id: int):
        """Delete a reminder by ID (used after sending notification)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM reminders WHERE id = ?",
                (reminder_id,)
            )
            await db.commit()

    @staticmethod
    def calc_next(remind_at_str: str, recurrence: str) -> str:
        """Calculate the next occurrence for a recurring reminder."""
        remind_at = datetime.strptime(remind_at_str, "%Y-%m-%d %H:%M:%S")

        if recurrence == "daily":
            next_at = remind_at + timedelta(days=1)

        elif recurrence == "weekday":
            next_at = remind_at + timedelta(days=1)
            while next_at.weekday() >= 5:  # Skip Saturday(5), Sunday(6)
                next_at += timedelta(days=1)

        elif recurrence.startswith("weekly:"):
            next_at = remind_at + timedelta(weeks=1)

        else:
            next_at = remind_at + timedelta(days=1)

        return next_at.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def recurrence_label(recurrence: str | None) -> str:
        """Get human-readable label for recurrence type."""
        if not recurrence:
            return ""
        if recurrence in RECURRENCE_LABELS:
            return RECURRENCE_LABELS[recurrence]
        if recurrence.startswith("weekly:"):
            day_num = int(recurrence.split(":")[1])
            day_names = ["월", "화", "수", "목", "금", "토", "일"]
            return f"매주 {day_names[day_num]}요일"
        return recurrence
