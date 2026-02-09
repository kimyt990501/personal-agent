from src.db.base import Database
from src.db.conversation import ConversationDB
from src.db.persona import PersonaDB
from src.db.memo import MemoDB
from src.db.reminder import ReminderDB


class DB:
    """Unified database access."""

    def __init__(self):
        self.base = Database()
        self.conversation = ConversationDB()
        self.persona = PersonaDB()
        self.memo = MemoDB()
        self.reminder = ReminderDB()

    async def init(self):
        """Initialize all database tables."""
        await self.base.init_db()
