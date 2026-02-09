import re
import asyncio
import aiohttp
import trafilatura
from typing import Optional
from ddgs import DDGS


URL_PATTERN = re.compile(
    r'https?://[^\s<>"{}|\\^`\[\]]+'
)


def extract_urls(text: str) -> list[str]:
    """Extract URLs from text."""
    return URL_PATTERN.findall(text)


async def fetch_page(url: str, timeout: int = 10) -> Optional[str]:
    """Fetch HTML content from URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    return await response.text()
    except Exception:
        pass
    return None


def extract_content(html: str) -> Optional[str]:
    """Extract main content from HTML using trafilatura."""
    return trafilatura.extract(html, include_comments=False, include_tables=True)


async def get_page_content(url: str) -> Optional[str]:
    """Fetch and extract main content from URL."""
    html = await fetch_page(url)
    if html:
        return extract_content(html)
    return None


async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web using DuckDuckGo."""
    def _search():
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                return results
        except Exception:
            return []

    # Run in thread pool since DDGS is synchronous
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, _search)
    return results


def format_search_results(results: list[dict]) -> str:
    """Format search results for LLM context."""
    if not results:
        return "검색 결과가 없습니다."

    formatted = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        body = r.get("body", "")
        url = r.get("href", "")
        formatted.append(f"{i}. **{title}**\n   {body}\n   링크: {url}")

    return "\n\n".join(formatted)
