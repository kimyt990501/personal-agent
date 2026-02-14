import discord
from discord import Message
from discord.ext import tasks

from src.config import DISCORD_TOKEN
from src.db import DB
from src.llm.ollama_client import OllamaClient
from src.utils.logger import setup_logger
from src.bot.handlers import (
    ChatHandler,
    MemoHandler,
    ReminderHandler,
    SearchHandler,
    PersonaHandler,
    CommandHandler,
    WeatherHandler,
    TranslateHandler,
    ExchangeHandler,
    PickHandler,
    FileHandler,
    FileSystemHandler,
    BriefingHandler,
)
from src.utils.briefing_generator import generate_briefing
from datetime import datetime

logger = setup_logger(__name__)


class PersonalAssistantBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        logger.info("Initializing PersonalAssistantBot")

        # Core components
        self.db = DB()
        self.ollama = OllamaClient()

        # Handlers
        self.cmd_handler = CommandHandler(self.db, self.ollama)
        self.chat_handler = ChatHandler(self.db, self.ollama)
        self.memo_handler = MemoHandler(self.db)
        self.reminder_handler = ReminderHandler(self.db)
        self.search_handler = SearchHandler(self.db, self.ollama)
        self.persona_handler = PersonaHandler(self.db)
        self.weather_handler = WeatherHandler()
        self.translate_handler = TranslateHandler(self.ollama)
        self.exchange_handler = ExchangeHandler()
        self.pick_handler = PickHandler()
        self.file_handler = FileHandler(self.ollama)
        self.fs_handler = FileSystemHandler(self.ollama)
        self.briefing_handler = BriefingHandler(self.db)

        # State
        self.persona_setup = {}

    async def setup_hook(self):
        """Called when the bot is starting up."""
        await self.db.init()
        logger.info("Database initialized")

        if await self.ollama.check_health():
            logger.info(f"Ollama connected: {self.ollama.model}")
        else:
            logger.warning(f"Ollama model '{self.ollama.model}' not available")

        self.check_reminders.start()
        logger.info("Reminder check loop started")

        self.check_briefing.start()
        logger.info("Briefing check loop started")

    async def on_ready(self):
        logger.info(f"Bot is ready: {self.user}")

    @tasks.loop(seconds=30)
    async def check_reminders(self):
        """Check and send due reminders."""
        try:
            due_reminders = await self.db.reminder.get_due()
            for reminder in due_reminders:
                try:
                    user = await self.fetch_user(int(reminder["user_id"]))
                    recurrence = reminder.get("recurrence")
                    if user:
                        label = self.db.reminder.recurrence_label(recurrence)
                        tag = f" 🔁{label}" if label else ""
                        await user.send(f"⏰ **리마인더**{tag}\n{reminder['content']}")
                    if recurrence:
                        next_at = self.db.reminder.calc_next(reminder["remind_at"], recurrence)
                        await self.db.reminder.reschedule(reminder["id"], next_at)
                    else:
                        await self.db.reminder.delete_by_id(reminder["id"])
                except Exception as e:
                    logger.error(f"Failed to send reminder: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Reminder check error: {e}", exc_info=True)

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.wait_until_ready()

    @tasks.loop(minutes=1)
    async def check_briefing(self):
        """Check and send daily briefings."""
        try:
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            current_date = now.strftime("%Y-%m-%d")

            enabled_users = await self.db.briefing.get_all_enabled()

            for settings in enabled_users:
                user_id = settings["user_id"]
                briefing_time = settings["time"]
                city = settings["city"]
                last_sent = settings.get("last_sent")

                # Check if already sent today
                if last_sent and last_sent.startswith(current_date):
                    continue  # Already sent today

                # Check if it's time to send (current time >= briefing time)
                brief_h, brief_m = map(int, briefing_time.split(":"))
                current_h, current_m = now.hour, now.minute

                # Send if current time is at or past briefing time
                if (current_h, current_m) >= (brief_h, brief_m):

                    try:
                        user = await self.fetch_user(int(user_id))
                        if user:
                            logger.info(f"Generating briefing for user {user_id}")
                            briefing_content = await generate_briefing(
                                city, user_id, self.db.reminder
                            )
                            await user.send(briefing_content)

                            # Update last_sent
                            await self.db.briefing.update_last_sent(
                                user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            )
                            logger.info(f"Briefing sent to user {user_id}")
                    except Exception as e:
                        logger.error(f"Failed to send briefing to {user_id}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Briefing check error: {e}", exc_info=True)

    @check_briefing.before_loop
    async def before_check_briefing(self):
        await self.wait_until_ready()

    async def on_message(self, message: Message):
        if message.author == self.user:
            return

        if not isinstance(message.channel, discord.DMChannel):
            return

        user_id = str(message.author.id)
        content = message.content.strip()
        cmd = content.lower()

        logger.debug(f"Message received from user {user_id}")

        # Route to appropriate handler
        if cmd == "/cmd":
            await self.cmd_handler.handle_help(message)
        elif cmd == "/ping":
            await self.cmd_handler.handle_ping(message)
        elif cmd == "/clear":
            await self.cmd_handler.handle_clear(message, user_id)
        elif cmd == "/newme":
            await self.cmd_handler.handle_newme(message, user_id, self.persona_setup)
        elif cmd == "/persona":
            await self.cmd_handler.handle_persona_info(message, user_id)
        elif cmd.startswith("/s "):
            query = content[3:].strip()
            persona = await self.db.persona.get(user_id)
            await self.search_handler.handle(message, user_id, query, persona)
        elif cmd.startswith("/m ") or cmd == "/m":
            await self.memo_handler.handle(message, user_id, content)
        elif cmd.startswith("/r ") or cmd == "/r":
            await self.reminder_handler.handle(message, user_id, content)
        elif cmd.startswith("/t ") or cmd == "/t":
            await self.translate_handler.handle(message, content)
        elif cmd.startswith("/ex ") or cmd == "/ex":
            await self.exchange_handler.handle(message, content)
        elif cmd.startswith("/pick ") or cmd == "/pick":
            await self.pick_handler.handle(message, content)
        elif cmd.startswith("/fs ") or cmd == "/fs":
            await self.fs_handler.handle(message, content)
        elif cmd.startswith("/w ") or cmd == "/w":
            await self.weather_handler.handle(message, content)
        elif cmd.startswith("/briefing"):
            args = content[9:].strip()  # Remove "/briefing"
            await self.briefing_handler.handle(message, user_id, args)
        elif message.attachments:
            await self.file_handler.handle(message, content)
        elif user_id in self.persona_setup:
            await self.persona_handler.handle_setup(message, user_id, content, self.persona_setup)
        else:
            persona = await self.db.persona.get(user_id)
            if not persona:
                await self.persona_handler.start_setup(message, user_id, self.persona_setup)
            else:
                await self.chat_handler.handle(message, user_id, content, persona)


def run_bot():
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN is not set in environment variables")

    bot = PersonalAssistantBot()
    bot.run(DISCORD_TOKEN)
