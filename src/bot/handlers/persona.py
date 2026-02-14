from discord import Message

from src.db import DB
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


PERSONA_SETUP_STEPS = {
    "name": "저를 뭐라고 불러주실 건가요? (예: 자비스, 비서, 알파 등)",
    "role": "제가 주로 어떤 역할을 하면 좋을까요? (예: 코딩 도우미, 일정 관리, 공부 도우미 등)",
    "tone": "어떤 말투를 사용할까요? (예: 친근한 반말, 공손한 존댓말, 유머러스하게 등)",
}


class PersonaHandler:
    """Handler for persona setup."""

    def __init__(self, db: DB):
        self.db = db

    async def start_setup(self, message: Message, user_id: str, persona_setup: dict):
        """Start the persona setup process."""
        persona_setup[user_id] = {"step": "name", "data": {}}
        await message.reply(
            "안녕하세요! 처음이시네요 👋\n"
            "저를 당신만의 AI 비서로 설정해볼까요?\n\n"
            f"**1/3** {PERSONA_SETUP_STEPS['name']}"
        )

    async def handle_setup(self, message: Message, user_id: str, content: str, persona_setup: dict):
        """Handle persona setup steps."""
        setup = persona_setup[user_id]
        current_step = setup["step"]

        # Save current answer
        setup["data"][current_step] = content

        # Move to next step
        steps = list(PERSONA_SETUP_STEPS.keys())
        current_index = steps.index(current_step)

        if current_index < len(steps) - 1:
            # Next question
            next_step = steps[current_index + 1]
            setup["step"] = next_step
            step_num = current_index + 2
            await message.reply(f"**{step_num}/3** {PERSONA_SETUP_STEPS[next_step]}")
        else:
            # Setup complete
            data = setup["data"]
            await self.db.persona.set(
                user_id,
                name=data["name"],
                role=data["role"],
                tone=data["tone"]
            )
            del persona_setup[user_id]

            await message.reply(
                f"설정 완료! \n\n"
                f"• 이름: **{data['name']}**\n"
                f"• 역할: **{data['role']}**\n"
                f"• 말투: **{data['tone']}**\n\n"
                f"이제 대화를 시작해보세요! (`/newme`로 다시 설정 가능)"
            )
