import aiosqlite
from src.config import DB_PATH
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class Database:
    """Base database class with connection management."""

    def __init__(self):
        self.db_path = DB_PATH

    async def init_db(self):
        """Initialize database and create all tables."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            # Conversations table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_id ON conversations(user_id)
            """)

            # Personas table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS personas (
                    user_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    tone TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Memos table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS memos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_memo_user_id ON memos(user_id)
            """)

            # Reminders table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    remind_at TIMESTAMP NOT NULL,
                    recurrence TEXT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_reminder_time ON reminders(remind_at)
            """)

            # Migration: add recurrence column if missing
            cursor = await db.execute("PRAGMA table_info(reminders)")
            columns = [row[1] for row in await cursor.fetchall()]
            if "recurrence" not in columns:
                await db.execute("ALTER TABLE reminders ADD COLUMN recurrence TEXT DEFAULT NULL")

            # Briefing settings table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS briefing_settings (
                    user_id TEXT PRIMARY KEY,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    time TEXT NOT NULL DEFAULT '08:00',
                    city TEXT NOT NULL DEFAULT '서울',
                    last_sent TEXT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Conversation summaries table (for context compression)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    user_id TEXT PRIMARY KEY,
                    summary TEXT NOT NULL,
                    message_count INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db.commit()
