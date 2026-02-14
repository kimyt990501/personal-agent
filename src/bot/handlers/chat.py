import re

import aiohttp
from discord import Message

from src.db import DB
from src.llm.ollama_client import OllamaClient
from src.utils.logger import setup_logger
from src.utils.web import extract_urls, get_page_content, web_search, format_search_results
from src.utils.weather import get_weather
from src.utils.time_parser import parse_time, format_datetime

logger = setup_logger(__name__)

# Tool call patterns
WEATHER_PATTERN = re.compile(r"\[WEATHER:(.+?)\]")
EXCHANGE_PATTERN = re.compile(r"\[EXCHANGE:(.+?),(.+?),(.+?)\]")
REMINDER_PATTERN = re.compile(r"\[REMINDER:(.+?),(.+)\]")
PERSONA_PATTERN = re.compile(r"\[PERSONA:(.+?),(.+?),(.+?)\]")
MEMO_SAVE_PATTERN = re.compile(r"\[MEMO_SAVE:(.+)\]")
MEMO_LIST_PATTERN = re.compile(r"\[MEMO_LIST\]")
MEMO_SEARCH_PATTERN = re.compile(r"\[MEMO_SEARCH:(.+)\]")
MEMO_DEL_PATTERN = re.compile(r"\[MEMO_DEL:(\d+)\]")
SEARCH_PATTERN = re.compile(r"\[SEARCH:(.+)\]")

EXCHANGE_API_URL = "https://open.er-api.com/v6/latest/{base}"
CURRENCY_NAMES = {
    "KRW": "한국 원",
    "USD": "미국 달러",
    "JPY": "일본 엔",
    "EUR": "유로",
    "GBP": "영국 파운드",
    "CNY": "중국 위안",
}

MAX_TOOL_ROUNDS = 3


class ChatHandler:
    """Handler for normal chat messages."""

    def __init__(self, db: DB, ollama: OllamaClient):
        self.db = db
        self.ollama = ollama

    async def handle(self, message: Message, user_id: str, user_content: str, persona: dict):
        """Handle normal chat with persona."""
        async with message.channel.typing():
            # Check for URLs and fetch content
            urls = extract_urls(user_content)
            url_contents = []

            for url in urls[:3]:
                content = await get_page_content(url)
                if content:
                    if len(content) > 4000:
                        content = content[:4000] + "...(truncated)"
                    url_contents.append(f"[Content from {url}]\n{content}")

            if url_contents:
                context = "\n\n".join(url_contents)
                enhanced_content = f"{user_content}\n\n---\n{context}"
            else:
                enhanced_content = user_content

            history = await self.db.conversation.get_history(user_id)
            history.append({"role": "user", "content": enhanced_content})

            try:
                response = await self._chat_with_tools(history, persona, user_id)

                await self.db.conversation.add_message(user_id, "user", user_content)
                await self.db.conversation.add_message(user_id, "assistant", response)

                await self._send_response(message, response)

            except Exception as e:
                logger.error(f"Chat handler error: {str(e)}", exc_info=True)
                await message.reply(f"오류가 발생했습니다: {str(e)}")

    async def _chat_with_tools(self, history: list[dict], persona: dict, user_id: str) -> str:
        """Chat with LLM, detecting and executing tool calls in a loop."""
        for _ in range(MAX_TOOL_ROUNDS):
            response = await self.ollama.chat(history, persona=persona)

            # Try each tool pattern
            tool_result = await self._try_weather(response)
            if tool_result is None:
                tool_result = await self._try_exchange(response)
            if tool_result is None:
                tool_result = await self._try_reminder(response, user_id)
            if tool_result is None:
                tool_result = await self._try_persona(response, user_id, persona)
            if tool_result is None:
                tool_result = await self._try_memo(response, user_id)
            if tool_result is None:
                tool_result = await self._try_search(response)

            # No tool call found → return as final response
            if tool_result is None:
                return response

            # Feed tool result back to LLM for natural response
            history.append({"role": "assistant", "content": response})
            history.append({"role": "user", "content": f"[Tool Result]\n{tool_result}\n\nBased on this data, answer the user's original question naturally."})

        return response

    async def _try_weather(self, response: str) -> str | None:
        """Check for weather tool call and execute if found."""
        match = WEATHER_PATTERN.search(response)
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

    async def _try_exchange(self, response: str) -> str | None:
        """Check for exchange tool call and execute if found."""
        match = EXCHANGE_PATTERN.search(response)
        if not match:
            return None

        try:
            amount = float(match.group(1).strip())
        except ValueError:
            amount = 1.0
        from_cur = match.group(2).strip().upper()
        to_cur = match.group(3).strip().upper()

        logger.info(f"Tool called: [EXCHANGE:{amount},{from_cur},{to_cur}]")

        rate = await self._fetch_rate(from_cur, to_cur)

        if rate is not None:
            result = amount * rate
            from_name = CURRENCY_NAMES.get(from_cur, from_cur)
            to_name = CURRENCY_NAMES.get(to_cur, to_cur)
            return (
                f"Exchange rate result:\n"
                f"- {amount:,.2f} {from_cur} ({from_name}) = {result:,.2f} {to_cur} ({to_name})\n"
                f"- Rate: 1 {from_cur} = {rate:,.4f} {to_cur}"
            )
        else:
            return f"Failed to get exchange rate for {from_cur} → {to_cur}. Please check the currency codes."

    async def _try_reminder(self, response: str, user_id: str) -> str | None:
        """Check for reminder tool call and execute if found."""
        match = REMINDER_PATTERN.search(response)
        if not match:
            return None

        time_str = match.group(1).strip()
        content = match.group(2).strip()

        logger.info(f"Tool called: [REMINDER:{time_str},{content}]")
        remind_at = parse_time(time_str)
        if not remind_at:
            return f"Failed to parse time '{time_str}'. Could not set the reminder."

        reminder_id = await self.db.reminder.add(
            user_id,
            content,
            remind_at.strftime("%Y-%m-%d %H:%M:%S"),
        )

        return (
            f"Reminder set successfully:\n"
            f"- ID: #{reminder_id}\n"
            f"- Time: {format_datetime(remind_at)}\n"
            f"- Content: {content}"
        )

    async def _try_persona(self, response: str, user_id: str, persona: dict) -> str | None:
        """Check for persona tool call and execute if found."""
        match = PERSONA_PATTERN.search(response)
        if not match:
            return None

        new_name = match.group(1).strip()
        new_role = match.group(2).strip()
        new_tone = match.group(3).strip()

        logger.info(f"Tool called: [PERSONA:{new_name},{new_role},{new_tone}]")

        # _ means keep current value
        name = new_name if new_name != "_" else persona.get("name", "AI")
        role = new_role if new_role != "_" else persona.get("role", "개인 비서")
        tone = new_tone if new_tone != "_" else persona.get("tone", "친근한 말투")

        await self.db.persona.set(user_id, name=name, role=role, tone=tone)

        # Update persona dict in-place so the next LLM call uses the new persona
        persona["name"] = name
        persona["role"] = role
        persona["tone"] = tone

        changes = []
        if new_name != "_":
            changes.append(f"- Name: {name}")
        if new_role != "_":
            changes.append(f"- Role: {role}")
        if new_tone != "_":
            changes.append(f"- Tone: {tone}")

        return "Persona updated successfully:\n" + "\n".join(changes)

    async def _try_memo(self, response: str, user_id: str) -> str | None:
        """Check for memo tool calls and execute if found."""
        # Try MEMO_SAVE
        match = MEMO_SAVE_PATTERN.search(response)
        if match:
            content = match.group(1).strip()
            logger.info(f"Tool called: [MEMO_SAVE:{content[:50]}...]")
            memo_id = await self.db.memo.add(user_id, content)
            return f"메모 저장 완료:\n- ID: #{memo_id}\n- 내용: {content}"

        # Try MEMO_LIST
        match = MEMO_LIST_PATTERN.search(response)
        if match:
            logger.info("Tool called: [MEMO_LIST]")
            memos = await self.db.memo.get_all(user_id, limit=20)
            if not memos:
                return "저장된 메모가 없습니다."
            
            lines = ["저장된 메모 목록:"]
            for memo in memos:
                lines.append(f"- #{memo['id']}: {memo['content']} (작성: {memo['created_at']})")
            return "\n".join(lines)

        # Try MEMO_SEARCH
        match = MEMO_SEARCH_PATTERN.search(response)
        if match:
            query = match.group(1).strip()
            logger.info(f"Tool called: [MEMO_SEARCH:{query}]")
            memos = await self.db.memo.search(user_id, query)
            if not memos:
                return f"'{query}' 검색 결과가 없습니다."
            
            lines = [f"'{query}' 검색 결과:"]
            for memo in memos:
                lines.append(f"- #{memo['id']}: {memo['content']} (작성: {memo['created_at']})")
            return "\n".join(lines)

        # Try MEMO_DEL
        match = MEMO_DEL_PATTERN.search(response)
        if match:
            position = int(match.group(1))  # 사용자가 말한 "N번째" (1부터 시작)
            logger.info(f"Tool called: [MEMO_DEL:{position}]")

            # 순서 → 실제 DB ID 변환
            memos = await self.db.memo.get_all(user_id, limit=20)
            if position < 1 or position > len(memos):
                return f"메모가 {len(memos)}개만 있습니다. {position}번째 메모를 찾을 수 없습니다."

            # memos는 최신순 정렬이므로 position-1 인덱스가 해당 메모
            target_memo = memos[position - 1]
            actual_id = target_memo['id']

            deleted = await self.db.memo.delete(user_id, actual_id)
            if deleted:
                return f"메모 삭제 완료:\n- #{actual_id}: {target_memo['content']}"
            else:
                return f"메모 #{actual_id}를 찾을 수 없습니다."

        return None

    async def _try_search(self, response: str) -> str | None:
        """Check for search tool call and execute if found."""
        match = SEARCH_PATTERN.search(response)
        if not match:
            return None

        query = match.group(1).strip()
        logger.info(f"Tool called: [SEARCH:{query}]")
        results = await web_search(query)

        if not results:
            return f"'{query}' 검색 결과를 가져오지 못했습니다."

        search_context = format_search_results(results)
        return f"검색 결과 ('{query}'):\n{search_context}"

    async def _fetch_rate(self, from_cur: str, to_cur: str) -> float | None:
        """Fetch exchange rate from API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(EXCHANGE_API_URL.format(base=from_cur)) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    if data.get("result") != "success":
                        return None
                    return data["rates"].get(to_cur)
        except Exception:
            return None

    async def _send_response(self, message: Message, response: str):
        """Send response, splitting if necessary."""
        if len(response) > 2000:
            chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
            for chunk in chunks:
                await message.reply(chunk)
        else:
            await message.reply(response)
