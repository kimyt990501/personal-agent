from src.db.base import Database
from src.db.conversation import ConversationDB
from src.db.persona import PersonaDB
from src.db.memo import MemoDB
from src.db.reminder import ReminderDB
from src.db.briefing import BriefingDB
from src.db.mail import MailDB


class DB:
    """Unified database access."""

    def __init__(self):
        self.base = Database()
        self.conversation = ConversationDB()
        self.persona = PersonaDB()
        self.memo = MemoDB()
        self.reminder = ReminderDB()
        self.briefing = BriefingDB()
        self.mail = MailDB()

    async def init(self):
        """Initialize all database tables."""
        await self.base.init_db()
