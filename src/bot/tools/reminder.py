import re

from src.bot.tools.base import Tool, ToolContext
from src.utils.logger import setup_logger
from src.utils.time_parser import parse_time, format_datetime

logger = setup_logger(__name__)


class ReminderTool(Tool):
    PATTERN = re.compile(r"\[REMINDER:(.+?),(.+)\]")

    @property
    def name(self) -> str:
        return "reminder"

    @property
    def description(self) -> str:
        return (
            "- Reminder: When the user wants to set a reminder, output [REMINDER:time,content]\n"
            "  - time: relative time like \"30분\", \"1시간\", \"2시간 30분\" or absolute time like \"14:00\", \"14시\", \"오후 2시\"\n"
            "  - content: what to remind about\n"
            "  - e.g. [REMINDER:30분,회의 시작], [REMINDER:14:00,점심 약속], [REMINDER:오후 3시,발표 준비]"
        )

    @property
    def usage_rules(self) -> str:
        return (
            "- For reminder, extract the time and what to remind. "
            "The user may say things like \"30분 후에 알려줘\", \"내일 회의 알려줘\", \"오후 3시에 약 먹으라고 알려줘\"."
        )

    async def try_execute(self, response: str, context: ToolContext) -> str | None:
        match = self.PATTERN.search(response)
        if not match:
            return None

        time_str = match.group(1).strip()
        content = match.group(2).strip()

        logger.info(f"Tool called: [REMINDER:{time_str},{content}]")
        remind_at = parse_time(time_str)
        if not remind_at:
            return f"Failed to parse time '{time_str}'. Could not set the reminder."

        reminder_id = await context.db.reminder.add(
            context.user_id,
            content,
            remind_at.strftime("%Y-%m-%d %H:%M:%S"),
        )

        return (
            f"Reminder set successfully:\n"
            f"- ID: #{reminder_id}\n"
            f"- Time: {format_datetime(remind_at)}\n"
            f"- Content: {content}"
        )
