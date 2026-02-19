import re

from src.bot.tools.base import Tool, ToolContext
from src.utils.logger import setup_logger
from src.utils.weather import get_weather

logger = setup_logger(__name__)


class WeatherTool(Tool):
    PATTERN = re.compile(r"\[WEATHER:(.+?)\]")

    @property
    def name(self) -> str:
        return "weather"

    @property
    def description(self) -> str:
        return "- Weather: When the user asks about weather, output [WEATHER:city_name] (e.g. [WEATHER:서울], [WEATHER:Tokyo])"

    @property
    def usage_rules(self) -> str:
        return "- For weather, extract the city name from the user's message."

    async def try_execute(self, response: str, context: ToolContext) -> str | None:
        match = self.PATTERN.search(response)
        if not match:
            return None

        city = match.group(1).strip()
        logger.info(f"Tool called: [WEATHER:{city}]")
        weather_data = await get_weather(city)

        if weather_data and "error" not in weather_data:
            lines = [
                f"Weather data for {weather_data['city']}:",
                f"- Condition: {weather_data['description']}",
                f"- Temperature: {weather_data['temp']}°C (feels like {weather_data['feels_like']}°C)",
                f"- Humidity: {weather_data['humidity']}%",
                f"- Wind: {weather_data['wind_speed']} m/s",
                f"- UV Index: {weather_data['uvi']}",
            ]
            if weather_data.get("temp_min") is not None:
                lines.append(f"- Low/High: {weather_data['temp_min']}°C / {weather_data['temp_max']}°C")
            if weather_data.get("rain_chance") is not None:
                lines.append(f"- Rain probability: {weather_data['rain_chance']}%")
            return "\n".join(lines)
        else:
            return f"Failed to get weather for '{city}'. The city may not exist or the API may be unavailable."
