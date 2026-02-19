import re

from src.bot.tools.base import Tool, ToolContext
from src.utils.logger import setup_logger
from src.utils.time_parser import validate_time_format

logger = setup_logger(__name__)


class BriefingTool(Tool):
    BRIEFING_SET_PATTERN = re.compile(r"\[BRIEFING_SET:(.+?),(.+)\]")
    BRIEFING_GET_PATTERN = re.compile(r"\[BRIEFING_GET\]")

    @property
    def name(self) -> str:
        return "briefing"

    @property
    def description(self) -> str:
        return (
            "- Briefing: When the user wants to change daily briefing settings or check current settings, use these tags:\n"
            "  - [BRIEFING_SET:key,value] - Change a setting (e.g. [BRIEFING_SET:time,07:00], [BRIEFING_SET:city,부산], [BRIEFING_SET:enabled,true/false])\n"
            "  - [BRIEFING_GET] - Get current briefing settings"
        )

    @property
    def usage_rules(self) -> str:
        return (
            "- For briefing, detect when the user wants to change settings "
            "(\"브리핑 7시로 바꿔줘\" → [BRIEFING_SET:time,07:00], \"브리핑 꺼줘\" → [BRIEFING_SET:enabled,false]) "
            "or check settings (\"브리핑 설정 알려줘\" → [BRIEFING_GET])."
        )

    async def try_execute(self, response: str, context: ToolContext) -> str | None:
        # Try BRIEFING_SET
        match = self.BRIEFING_SET_PATTERN.search(response)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            logger.info(f"Tool called: [BRIEFING_SET:{key},{value}]")

            if key == "time":
                is_valid, error_msg = validate_time_format(value)
                if not is_valid:
                    return error_msg

                await context.db.briefing.set_settings(context.user_id, time=value)
                return f"브리핑 시간이 {value}로 설정되었습니다."

            elif key == "city":
                await context.db.briefing.set_settings(context.user_id, city=value)
                return f"브리핑 도시가 {value}로 설정되었습니다."

            elif key == "enabled":
                enabled = value.lower() in ("true", "1", "on", "yes")
                await context.db.briefing.set_settings(context.user_id, enabled=enabled)
                status = "활성화" if enabled else "비활성화"
                return f"브리핑이 {status}되었습니다."

            else:
                return f"알 수 없는 설정 항목: {key}"

        # Try BRIEFING_GET
        match = self.BRIEFING_GET_PATTERN.search(response)
        if match:
            logger.info("Tool called: [BRIEFING_GET]")
            settings = await context.db.briefing.get_settings(context.user_id)

            if settings is None:
                return "브리핑 설정 (기본값):\n- 상태: 활성화\n- 시간: 08:00\n- 도시: 서울"
            else:
                status = "활성화" if settings["enabled"] else "비활성화"
                return (
                    f"브리핑 설정:\n"
                    f"- 상태: {status}\n"
                    f"- 시간: {settings['time']}\n"
                    f"- 도시: {settings['city']}\n"
                    f"- 마지막 발송: {settings['last_sent'] or '없음'}"
                )

        return None
