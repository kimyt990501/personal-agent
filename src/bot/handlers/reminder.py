import re
from discord import Message

from src.db import DB
from src.db.reminder import ReminderDB
from src.utils.time_parser import parse_time, format_datetime

DAY_MAP = {
    "월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6,
}


class ReminderHandler:
    """Handler for reminder commands."""

    def __init__(self, db: DB):
        self.db = db

    async def handle(self, message: Message, user_id: str, content: str):
        """Handle reminder commands."""
        parts = content.split(maxsplit=2)

        # /r alone
        if len(parts) == 1:
            await self._show_help(message)
            return

        cmd = parts[1].lower()

        if cmd == "list":
            await self._list_reminders(message, user_id)
        elif cmd == "del":
            await self._delete_reminder(message, user_id, parts)
        elif cmd in ("daily", "weekday") or cmd.startswith("weekly"):
            await self._set_recurring_reminder(message, user_id, content)
        else:
            await self._set_reminder(message, user_id, content)

    async def _show_help(self, message: Message):
        """Show reminder help."""
        await message.reply(
            "**⏰ 리마인더 사용법**\n"
            "`/r <시간> <내용>` - 1회 리마인더\n"
            "`/r list` - 리마인더 목록\n"
            "`/r del <번호>` - 리마인더 삭제\n\n"
            "**반복 리마인더**\n"
            "`/r daily <시간> <내용>` - 매일\n"
            "`/r weekday <시간> <내용>` - 평일만\n"
            "`/r weekly <요일> <시간> <내용>` - 매주\n"
            "예: `/r daily 18:00 퇴근`\n"
            "예: `/r weekday 9:00 출근`\n"
            "예: `/r weekly 금 17:00 회식`\n\n"
            "**시간 형식**\n"
            "`30분`, `1시간`, `14:00`, `14시`, `오후 2시`"
        )

    async def _list_reminders(self, message: Message, user_id: str):
        """List all reminders."""
        reminders = await self.db.reminder.get_all(user_id)
        if not reminders:
            await message.reply("설정된 리마인더가 없어요.")
            return

        reminder_list = []
        for r in reminders:
            time_str = format_datetime(r['remind_at'])
            preview = r['content'][:40] + "..." if len(r['content']) > 40 else r['content']
            label = ReminderDB.recurrence_label(r.get('recurrence'))
            repeat_tag = f" 🔁{label}" if label else ""
            reminder_list.append(f"`{r['id']}` [{time_str}]{repeat_tag} {preview}")

        await message.reply("**⏰ 리마인더 목록**\n" + "\n".join(reminder_list))

    async def _delete_reminder(self, message: Message, user_id: str, parts: list):
        """Delete a reminder."""
        if len(parts) < 3:
            await message.reply("삭제할 리마인더 번호를 입력해주세요. 예: `/r del 1`")
            return

        try:
            reminder_id = int(parts[2])
            deleted = await self.db.reminder.delete(user_id, reminder_id)
            if deleted:
                await message.reply(f"리마인더 #{reminder_id} 삭제 완료!")
            else:
                await message.reply(f"리마인더 #{reminder_id}를 찾을 수 없어요.")
        except ValueError:
            await message.reply("올바른 리마인더 번호를 입력해주세요.")

    async def _set_recurring_reminder(self, message: Message, user_id: str, content: str):
        """Set a recurring reminder."""
        rest = content[3:].strip()  # Remove "/r "
        parts = rest.split()

        recurrence_type = parts[0].lower()
        remaining = parts[1:]

        # Parse recurrence
        if recurrence_type == "weekly":
            if len(remaining) < 3:
                await message.reply("사용법: `/r weekly <요일> <시간> <내용>`\n예: `/r weekly 금 17:00 회식`")
                return
            day_str = remaining[0]
            if day_str not in DAY_MAP:
                await message.reply(f"요일을 인식하지 못했어요. 사용 가능: {', '.join(DAY_MAP.keys())}")
                return
            recurrence = f"weekly:{DAY_MAP[day_str]}"
            remaining = remaining[1:]
        else:
            # daily or weekday
            if len(remaining) < 2:
                await message.reply(f"사용법: `/r {recurrence_type} <시간> <내용>`\n예: `/r {recurrence_type} 18:00 퇴근`")
                return
            recurrence = recurrence_type

        # Parse time and content from remaining
        time_str, reminder_content = self._extract_time_and_content(" ".join(remaining))

        if not time_str or not reminder_content:
            await message.reply("시간과 내용을 입력해주세요.\n예: `/r daily 18:00 퇴근`")
            return

        remind_at = parse_time(time_str)
        if not remind_at:
            await message.reply(f"'{time_str}'을(를) 인식하지 못했어요.")
            return

        reminder_id = await self.db.reminder.add(
            user_id,
            reminder_content,
            remind_at.strftime("%Y-%m-%d %H:%M:%S"),
            recurrence=recurrence,
        )

        label = ReminderDB.recurrence_label(recurrence)
        await message.reply(
            f"🔁 반복 리마인더 설정 완료! (#{reminder_id})\n"
            f"**반복:** {label}\n"
            f"**시간:** {format_datetime(remind_at)}\n"
            f"**내용:** {reminder_content}"
        )

    async def _set_reminder(self, message: Message, user_id: str, content: str):
        """Set a one-time reminder."""
        rest = content[3:].strip()  # Remove "/r "

        time_str, reminder_content = self._extract_time_and_content(rest)

        if not time_str or not reminder_content:
            await message.reply(
                "시간과 내용을 입력해주세요.\n"
                "예: `/r 30분 회의 시작`\n"
                "예: `/r 14:00 점심 약속`"
            )
            return

        remind_at = parse_time(time_str)
        if not remind_at:
            await message.reply(f"'{time_str}'을(를) 인식하지 못했어요. 다시 시도해주세요.")
            return

        reminder_id = await self.db.reminder.add(
            user_id,
            reminder_content,
            remind_at.strftime("%Y-%m-%d %H:%M:%S")
        )

        await message.reply(
            f"⏰ 리마인더 설정 완료! (#{reminder_id})\n"
            f"**시간:** {format_datetime(remind_at)}\n"
            f"**내용:** {reminder_content}"
        )

    def _extract_time_and_content(self, text: str) -> tuple[str | None, str | None]:
        """Extract time string and remaining content from text."""
        time_patterns = [
            r'^(\d+분)\s+',
            r'^(\d+시간)\s+',
            r'^(\d+시간\s*\d+분)\s+',
            r'^(\d+일)\s+',
            r'^(\d{1,2}:\d{2})\s+',
            r'^(\d{1,2}시(?:\s*\d{1,2}분)?)\s+',
            r'^(오[전후]\s*\d{1,2}시(?:\s*\d{1,2}분)?)\s+',
        ]

        for pattern in time_patterns:
            match = re.match(pattern, text)
            if match:
                return match.group(1), text[match.end():].strip()

        return None, None
