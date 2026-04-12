"""
Tavily web search layer for MAGI.
Falls back to an empty result set if TAVILY_API_KEY is not set,
so deliberation continues on internal knowledge only.
"""
import os
from dataclasses import dataclass


@dataclass
class SearchResult:
    title: str
    content: str
    url: str


# Per-agent, per-round query templates — each shaped by the fragment's lens
_QUERY_TEMPLATES: dict[str, dict[str, str]] = {
    "MELCHIOR": {
        "r1": "{topic} empirical evidence data research findings",
        "r2": "{topic} scientific consensus criticism limitations",
    },
    "BALTHASAR": {
        "r1": "{topic} population outcomes mortality risk societal impact",
        "r2": "{topic} long-term consequences survival policy tradeoffs",
    },
    "CASPAR": {
        "r1": "{topic} human experience dignity meaning quality of life",
        "r2": "{topic} personal accounts psychological impact individual rights",
    },
}


def make_query(agent_key: str, round_name: str, topic: str) -> str:
    template = _QUERY_TEMPLATES.get(agent_key, {}).get(round_name, "{topic}")
    return template.format(topic=topic)


async def web_search(query: str) -> list[SearchResult]:
    """
    Run a Tavily search and return up to 3 results.
    Returns [] immediately if TAVILY_API_KEY is unset (mock/fallback mode).
    """
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        return []
    try:
        from tavily import AsyncTavilyClient  # imported lazily — not required at startup
        client = AsyncTavilyClient(api_key=api_key)
        resp = await client.search(query, max_results=3, search_depth="basic")
        return [
            SearchResult(
                title=r.get("title", ""),
                content=r.get("content", "")[:350].strip(),
                url=r.get("url", ""),
            )
            for r in resp.get("results", [])[:3]
        ]
    except Exception:
        return []


def format_for_context(results: list[SearchResult]) -> str:
    """Format results as a compact block for injection into the agent prompt."""
    if not results:
        return ""
    lines = ["[EXTERNAL FEED — SEARCH RESULTS]"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r.title}")
        if r.content:
            lines.append(f"   {r.content}")
    return "\n".join(lines)
