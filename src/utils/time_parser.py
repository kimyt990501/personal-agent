import re
from datetime import datetime, timedelta

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def parse_time(time_str: str) -> datetime | None:
    """
    Parse time string and return datetime.

    Supports:
    - Relative: "30분", "1시간", "2시간 30분", "1일"
    - Absolute: "14:00", "14시", "14시 30분", "오후 2시"
    """
    time_str = time_str.strip()
    now = datetime.now()

    # Relative time patterns
    # "30분", "30분 후"
    match = re.match(r'^(\d+)\s*분(?:\s*후)?$', time_str)
    if match:
        minutes = int(match.group(1))
        return now + timedelta(minutes=minutes)

    # "1시간", "1시간 후"
    match = re.match(r'^(\d+)\s*시간(?:\s*후)?$', time_str)
    if match:
        hours = int(match.group(1))
        return now + timedelta(hours=hours)

    # "1시간 30분"
    match = re.match(r'^(\d+)\s*시간\s*(\d+)\s*분(?:\s*후)?$', time_str)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        return now + timedelta(hours=hours, minutes=minutes)

    # "1일", "1일 후"
    match = re.match(r'^(\d+)\s*일(?:\s*후)?$', time_str)
    if match:
        days = int(match.group(1))
        return now + timedelta(days=days)

    # Absolute time patterns
    # "14:00", "14:30"
    match = re.match(r'^(\d{1,2}):(\d{2})$', time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target

    # "14시", "14시 30분"
    match = re.match(r'^(\d{1,2})시(?:\s*(\d{1,2})분)?$', time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target

    # "오전 9시", "오후 2시", "오후 2시 30분"
    match = re.match(r'^(오전|오후)\s*(\d{1,2})시(?:\s*(\d{1,2})분)?$', time_str)
    if match:
        period = match.group(1)
        hour = int(match.group(2))
        minute = int(match.group(3)) if match.group(3) else 0

        if period == "오후" and hour != 12:
            hour += 12
        elif period == "오전" and hour == 12:
            hour = 0

        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target

    return None


def format_datetime(dt: datetime | str) -> str:
    """Format datetime for display."""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    return dt.strftime("%m/%d %H:%M")


def validate_time_format(time_str: str) -> tuple[bool, str | None]:
    """
    Validate HH:MM time format.

    Returns:
        (is_valid, error_message): tuple where error_message is None if valid
    """
    if ":" not in time_str or len(time_str.split(":")) != 2:
        return False, "시간 형식이 올바르지 않습니다. 예: 08:00"

    try:
        h, m = time_str.split(":")
        hour = int(h)
        minute = int(m)

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return False, "시간이 올바르지 않습니다. (시: 0-23, 분: 0-59)"

        return True, None
    except ValueError:
        return False, "시간 형식이 올바르지 않습니다. 예: 08:00"
