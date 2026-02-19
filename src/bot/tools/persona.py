import re

from src.bot.tools.base import Tool, ToolContext
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class PersonaTool(Tool):
    PATTERN = re.compile(r"\[PERSONA:(.+?),(.+?),(.+?)\]")

    @property
    def name(self) -> str:
        return "persona"

    @property
    def description(self) -> str:
        return (
            "- Persona: When the user wants to change your name, role, or speaking style, output [PERSONA:name,role,tone]\n"
            "  - name: new name (use _ to keep current)\n"
            "  - role: new role description (use _ to keep current)\n"
            "  - tone: new speaking style (use _ to keep current)\n"
            "  - e.g. [PERSONA:뽀삐,_,_] (change name only), [PERSONA:_,_,반말] (change tone only), [PERSONA:제이,비서,존댓말] (change all)"
        )

    @property
    def usage_rules(self) -> str:
        return (
            "- For persona, only use when the user explicitly asks to change your name, role, or tone. "
            "Use _ for fields that should stay the same."
        )

    async def try_execute(self, response: str, context: ToolContext) -> str | None:
        match = self.PATTERN.search(response)
        if not match:
            return None

        new_name = match.group(1).strip()
        new_role = match.group(2).strip()
        new_tone = match.group(3).strip()

        logger.info(f"Tool called: [PERSONA:{new_name},{new_role},{new_tone}]")

        # _ means keep current value
        name = new_name if new_name != "_" else context.persona.get("name", "AI")
        role = new_role if new_role != "_" else context.persona.get("role", "개인 비서")
        tone = new_tone if new_tone != "_" else context.persona.get("tone", "친근한 말투")

        await context.db.persona.set(context.user_id, name=name, role=role, tone=tone)

        # Update persona dict in-place so the next LLM call uses the new persona
        context.persona["name"] = name
        context.persona["role"] = role
        context.persona["tone"] = tone

        changes = []
        if new_name != "_":
            changes.append(f"- Name: {name}")
        if new_role != "_":
            changes.append(f"- Role: {role}")
        if new_tone != "_":
            changes.append(f"- Tone: {tone}")

        return "Persona updated successfully:\n" + "\n".join(changes)
