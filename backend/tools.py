"""
ReAct tool implementations for the MAGI system.
Four tools available to each Magi agent during deliberation:
  - web_search           : Search the web for current information
  - get_counterargument  : Steelman the opposite of a claim (llama-3.1-8b-instant)
  - cite_source          : Fetch + summarise a URL (llama-3.1-8b-instant)
  - calculate_consensus  : Check how claims align with prior debate text
"""

from __future__ import annotations

import os
import re
from typing import Any

import httpx
from groq import AsyncGroq

# ── Tool schemas for Groq function calling ─────────────────────────────────────

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web for recent data, studies, or facts relevant to the debate topic. "
                "Use this when you need concrete evidence to support or attack a claim."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A focused search query — 10 words or fewer.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_counterargument",
            "description": (
                "Generate the strongest possible counterargument to a claim. "
                "Use this to stress-test your own position or anticipate an opponent's rebuttal."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "claim": {
                        "type": "string",
                        "description": "The claim you want to stress-test.",
                    }
                },
                "required": ["claim"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cite_source",
            "description": (
                "Fetch a URL and extract a brief factual summary of its content. "
                "Use this when you have a specific URL whose contents you want to cite as evidence."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full URL to fetch.",
                    }
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_consensus",
            "description": (
                "Analyse how a list of claims aligns with the positions taken by other Magi fragments "
                "in this debate so far. Use this in Round 2 to calibrate your response to existing disagreements."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "claims": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "1–4 claims to check against the current debate context.",
                    }
                },
                "required": ["claims"],
            },
        },
    },
]

# ── Tool implementations ────────────────────────────────────────────────────────

_SMALL_MODEL = "llama-3.1-8b-instant"


async def tool_web_search(query: str) -> str:
    try:
        from tavily import AsyncTavilyClient  # lazy import — optional dependency
        key = os.environ.get("TAVILY_API_KEY", "")
        if not key:
            return "TAVILY_API_KEY not set — web search unavailable."
        c = AsyncTavilyClient(api_key=key)
        results = (await c.search(query, max_results=3)).get("results", [])
        if not results:
            return "No results found."
        return "\n\n".join(
            f"[{r.get('title', 'Untitled')}]\n{r.get('content', '')[:300]}"
            for r in results
        )
    except Exception as exc:
        return f"Search error: {exc}"


async def tool_get_counterargument(claim: str, client: AsyncGroq) -> str:
    try:
        resp = await client.chat.completions.create(
            model=_SMALL_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a rigorous debate analyst. "
                        "Produce the single strongest factual counterargument to the given claim. "
                        "Be specific, avoid straw-men, stay under 80 words."
                    ),
                },
                {"role": "user", "content": f"Claim: {claim}"},
            ],
            max_tokens=120,
            temperature=0.7,
        )
        return resp.choices[0].message.content or "No counterargument generated."
    except Exception as exc:
        return f"Tool error: {exc}"


async def tool_cite_source(url: str, client: AsyncGroq) -> str:
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as http:
            r = await http.get(url, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            raw = r.text
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\s+", " ", text).strip()[:2000]
        resp = await client.chat.completions.create(
            model=_SMALL_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract and summarise the key factual claim or finding from this web content. "
                        "Under 80 words. Be specific and factual."
                    ),
                },
                {"role": "user", "content": text},
            ],
            max_tokens=120,
            temperature=0.3,
        )
        return resp.choices[0].message.content or "Could not summarise source."
    except Exception as exc:
        return f"Could not fetch source: {exc}"


async def tool_calculate_consensus(
    claims: list[str],
    debate_context: str,
    client: AsyncGroq,
) -> str:
    if not debate_context.strip():
        return "No prior debate context — consensus check not applicable in Round 1."
    try:
        claims_text = "\n".join(f"- {c}" for c in claims)
        resp = await client.chat.completions.create(
            model=_SMALL_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You analyse alignment within a multi-agent debate. "
                        "Given the debate so far and a list of claims, state briefly: "
                        "which fragment would agree, which would disagree, and overall consensus strength. "
                        "Under 100 words."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Debate so far:\n{debate_context}\n\nClaims:\n{claims_text}",
                },
            ],
            max_tokens=150,
            temperature=0.4,
        )
        return resp.choices[0].message.content or "No consensus analysis."
    except Exception as exc:
        return f"Consensus error: {exc}"


# ── Dispatcher ─────────────────────────────────────────────────────────────────

async def execute_tool(
    name: str,
    args: dict[str, Any],
    client: AsyncGroq,
    debate_context: str = "",
) -> str:
    if name == "web_search":
        return await tool_web_search(args.get("query", ""))
    if name == "get_counterargument":
        return await tool_get_counterargument(args.get("claim", ""), client)
    if name == "cite_source":
        return await tool_cite_source(args.get("url", ""), client)
    if name == "calculate_consensus":
        return await tool_calculate_consensus(args.get("claims", []), debate_context, client)
    return f"Unknown tool: {name}"
