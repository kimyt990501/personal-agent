import ollama
from ollama import AsyncClient

from src.config import OLLAMA_HOST, OLLAMA_MODEL
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class OllamaClient:
    def __init__(self, host: str = OLLAMA_HOST, model: str = OLLAMA_MODEL):
        self.client = AsyncClient(host=host)
        self.model = model

    def build_system_prompt(self, persona: dict | None = None) -> str:
        """Build system prompt with optional persona."""
        tool_instructions = """

You have access to the following tools. When you need real-time information or to perform an action, use them by outputting the exact tag format.
IMPORTANT: Output ONLY the tag with no other text when you use a tool.

Available tools:
- Weather: When the user asks about weather, output [WEATHER:city_name] (e.g. [WEATHER:서울], [WEATHER:Tokyo])
- Exchange: When the user asks about currency exchange rates, output [EXCHANGE:amount,FROM,TO] (e.g. [EXCHANGE:100,USD,KRW], [EXCHANGE:1,JPY,KRW])
  - amount: the numeric amount to convert (default 1 if not specified)
  - FROM/TO: 3-letter currency codes (e.g. USD, KRW, JPY, EUR, GBP, CNY)
- Reminder: When the user wants to set a reminder, output [REMINDER:time,content]
  - time: relative time like "30분", "1시간", "2시간 30분" or absolute time like "14:00", "14시", "오후 2시"
  - content: what to remind about
  - e.g. [REMINDER:30분,회의 시작], [REMINDER:14:00,점심 약속], [REMINDER:오후 3시,발표 준비]
- Persona: When the user wants to change your name, role, or speaking style, output [PERSONA:name,role,tone]
  - name: new name (use _ to keep current)
  - role: new role description (use _ to keep current)
  - tone: new speaking style (use _ to keep current)
  - e.g. [PERSONA:뽀삐,_,_] (change name only), [PERSONA:_,_,반말] (change tone only), [PERSONA:제이,비서,존댓말] (change all)
- Memo: When the user wants to save, list, search, or delete memos, use these tags:
  - [MEMO_SAVE:content] - Save a new memo (e.g. [MEMO_SAVE:우유 사기], [MEMO_SAVE:프로젝트 마감일 금요일])
  - [MEMO_LIST] - List all saved memos
  - [MEMO_SEARCH:keyword] - Search memos containing the keyword (e.g. [MEMO_SEARCH:우유], [MEMO_SEARCH:회의])
  - [MEMO_DEL:position] - Delete a memo by position in the list (e.g. [MEMO_DEL:1] for first, [MEMO_DEL:2] for second)
    IMPORTANT: Use the position number (1st, 2nd, 3rd...) from the list, NOT the database ID
- Search: When the user asks about recent events, current information, or anything requiring up-to-date data beyond your knowledge, output [SEARCH:query]
  - e.g. [SEARCH:비트코인 시세], [SEARCH:파이썬 3.13 새 기능], [SEARCH:2026 아이폰 출시일]
  - Use only when your knowledge is insufficient or the user explicitly asks you to search the web
- Briefing: When the user wants to change daily briefing settings or check current settings, use these tags:
  - [BRIEFING_SET:key,value] - Change a setting (e.g. [BRIEFING_SET:time,07:00], [BRIEFING_SET:city,부산], [BRIEFING_SET:enabled,true/false])
  - [BRIEFING_GET] - Get current briefing settings

Rules:
- Use tools only when the user is clearly asking for real-time information or requesting an action.
- For weather, extract the city name from the user's message.
- For exchange, extract the amount and currency codes. If the user says "달러" assume USD, "엔" assume JPY, "원" assume KRW, "유로" assume EUR, "위안" assume CNY, "파운드" assume GBP.
- For reminder, extract the time and what to remind. The user may say things like "30분 후에 알려줘", "내일 회의 알려줘", "오후 3시에 약 먹으라고 알려줘".
- For persona, only use when the user explicitly asks to change your name, role, or tone. Use _ for fields that should stay the same.
- For memo, detect when the user wants to save information for later ("메모해줘", "기억해줘", "저장해줘"), list memos ("메모 뭐 있었지", "메모 목록"), search ("메모 찾아줘", "~에 대한 메모"), or delete ("메모 삭제", "메모 지워줘", "첫 번째 메모 삭제"). When deleting, extract the position number (1st=1, 2nd=2, 3rd=3, etc.).
- For search, use when the question requires current/recent information or the user explicitly asks to search. Extract the core search query from their question.
- For briefing, detect when the user wants to change settings ("브리핑 7시로 바꿔줘" → [BRIEFING_SET:time,07:00], "브리핑 꺼줘" → [BRIEFING_SET:enabled,false]) or check settings ("브리핑 설정 알려줘" → [BRIEFING_GET]).
- For translation requests ("번역해줘", "영어로", "translate this"), directly translate without using any tool tag. You have built-in multilingual capabilities.
- Output ONLY the tool tag, nothing else. Do not add any explanation before or after the tag."""

        if persona:
            return f"""You are {persona['name']}, a personal AI assistant.
Your role: {persona['role']}
Your tone/style: {persona['tone']}

You are running locally on the user's Mac Mini via Ollama ({self.model}).
Always stay in character. Answer in the same language the user uses.
Never claim to be Claude, ChatGPT, or any other AI.
{tool_instructions}"""
        else:
            return f"""You are a personal AI assistant powered by {self.model}.
You are running locally on the user's Mac Mini via Ollama.
Be concise, helpful, and friendly. Answer in the same language the user uses.
Never claim to be Claude, ChatGPT, or any other AI.
{tool_instructions}"""

    async def chat(self, messages: list[dict], persona: dict | None = None) -> str:
        """Send messages to Ollama and get a response."""
        system_prompt = self.build_system_prompt(persona)

        full_messages = [
            {"role": "system", "content": system_prompt},
            *messages
        ]

        response = await self.client.chat(
            model=self.model,
            messages=full_messages,
        )

        return response["message"]["content"]

    async def check_health(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            response = await self.client.list()
            model_names = [m.model for m in response.models]
            return any(self.model in name for name in model_names)
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False
