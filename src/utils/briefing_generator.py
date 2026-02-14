"""Daily briefing content generator."""

from datetime import datetime, date
from src.utils.weather import get_weather
from src.utils.web import web_search, format_search_results
from src.db.reminder import ReminderDB
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def generate_briefing(city: str, user_id: str, reminder_db: ReminderDB) -> str:
    """Generate daily briefing content.

    Args:
        city: City for weather
        user_id: User ID for reminders
        reminder_db: ReminderDB instance

    Returns:
        Formatted briefing message
    """
    sections = []
    today = date.today().strftime("%Y-%m-%d")

    # Header
    sections.append(f"☀️ **일일 브리핑** - {datetime.now().strftime('%Y년 %m월 %d일 %A')}")
    sections.append("")

    # 1. Weather
    try:
        weather_data = await get_weather(city)
        if weather_data and "error" not in weather_data:
            sections.append("🌤️ **날씨**")
            sections.append(f"**{weather_data['city']}** - {weather_data['description']}")
            sections.append(f"🌡️ 기온: {weather_data['temp']}°C (체감 {weather_data['feels_like']}°C)")
            if weather_data.get("temp_min") and weather_data.get("temp_max"):
                sections.append(f"📊 최저/최고: {weather_data['temp_min']}°C / {weather_data['temp_max']}°C")
            if weather_data.get("rain_chance"):
                sections.append(f"☔ 강수확률: {weather_data['rain_chance']}%")
            sections.append(f"💧 습도: {weather_data['humidity']}%")
            sections.append("")
        else:
            logger.warning(f"Weather fetch failed for {city}")
            sections.append("🌤️ **날씨**: 정보를 가져올 수 없습니다.")
            sections.append("")
    except Exception as e:
        logger.error(f"Weather error in briefing: {e}", exc_info=True)
        sections.append("🌤️ **날씨**: 정보를 가져올 수 없습니다.")
        sections.append("")

    # 2. Today's reminders
    try:
        all_reminders = await reminder_db.get_all(user_id)
        today_reminders = [r for r in all_reminders if r["remind_at"].startswith(today)]

        sections.append("📅 **오늘의 리마인더**")
        if today_reminders:
            for reminder in today_reminders:
                time = reminder["remind_at"].split(" ")[1][:5]  # HH:MM
                sections.append(f"- {time} | {reminder['content']}")
        else:
            sections.append("오늘 예정된 리마인더가 없습니다.")
        sections.append("")
    except Exception as e:
        logger.error(f"Reminder error in briefing: {e}", exc_info=True)
        sections.append("📅 **오늘의 리마인더**: 정보를 가져올 수 없습니다.")
        sections.append("")

    # 3. News headlines
    try:
        results = await web_search("오늘 주요 뉴스 한국")
        if results:
            formatted = format_search_results(results)
            # Take first 3-5 results
            lines = formatted.split("\n")
            headlines = []
            for line in lines[:15]:  # First 15 lines should cover 3-5 results
                if line.strip():
                    headlines.append(line)

            sections.append("📰 **주요 뉴스**")
            sections.extend(headlines[:10])  # Limit to 10 lines
            sections.append("")
        else:
            logger.warning("News search failed")
            sections.append("📰 **주요 뉴스**: 정보를 가져올 수 없습니다.")
            sections.append("")
    except Exception as e:
        logger.error(f"News error in briefing: {e}", exc_info=True)
        sections.append("📰 **주요 뉴스**: 정보를 가져올 수 없습니다.")
        sections.append("")

    # Footer
    sections.append("---")
    sections.append("💡 좋은 하루 되세요!")

    return "\n".join(sections)
