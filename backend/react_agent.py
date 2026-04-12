"""
ReAct agentic loop for each MAGI fragment.

run_react_agent() is an async generator that:
  1. Sends the user message to the model with all tool schemas attached
  2. Executes any requested tool calls (up to MAX_STEPS rounds)
  3. Yields trace events so the UI can show the inner monologue
  4. Streams the final answer as token events

Yielded event dict shapes:
  {"type": "trace_thought", "agent": str, "round": str, "text": str}
  {"type": "trace_action",  "agent": str, "round": str, "tool": str, "args": dict}
  {"type": "trace_obs",     "agent": str, "round": str, "text": str}
  {"type": "search_query",  "agent": str, "round": str, "query": str, "live": bool}
  {"type": "token",         "agent": str, "round": str, "text": str}
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator
from typing import Any

from groq import AsyncGroq

from .tools import TOOL_SCHEMAS, execute_tool

MAX_STEPS = 4
_MAIN_MODEL = "llama-3.3-70b-versatile"


async def run_react_agent(
    client: AsyncGroq,
    agent_key: str,
    round_name: str,
    system_prompt: str,
    user_message: str,
    debate_context: str = "",
    max_tokens: int = 220,
) -> AsyncGenerator[dict[str, Any], None]:
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    # ── ReAct tool loop ─────────────────────────────────────────────────────────
    for _ in range(MAX_STEPS):
        response = await client.chat.completions.create(
            model=_MAIN_MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            max_tokens=400,
            temperature=0.7,
        )

        msg = response.choices[0].message
        tool_calls = msg.tool_calls or []

        # Emit any thinking text the model produced before (or instead of) a tool call
        if msg.content and msg.content.strip():
            yield {
                "type": "trace_thought",
                "agent": agent_key,
                "round": round_name,
                "text": msg.content.strip(),
            }

        # No tool call → the model has decided it's ready to answer
        if not tool_calls:
            break

        # Append the assistant turn (with tool calls) to history
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in tool_calls
            ],
        })

        # ── Execute each tool call ───────────────────────────────────────────────
        for tc in tool_calls:
            name = tc.function.name
            try:
                args: dict = json.loads(tc.function.arguments)
            except (json.JSONDecodeError, ValueError):
                args = {}

            # Trace the action
            yield {
                "type": "trace_action",
                "agent": agent_key,
                "round": round_name,
                "tool": name,
                "args": args,
            }

            # Emit a search_query event for web_search calls so the UI icon updates
            if name == "web_search":
                yield {
                    "type": "search_query",
                    "agent": agent_key,
                    "round": round_name,
                    "query": args.get("query", ""),
                    "live": bool(os.environ.get("TAVILY_API_KEY", "")),
                }

            # Run the tool
            observation = await execute_tool(name, args, client, debate_context)

            # Trace the observation
            yield {
                "type": "trace_obs",
                "agent": agent_key,
                "round": round_name,
                "text": observation,
            }

            # Feed the result back into the conversation
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": observation,
            })

    # ── Final streaming answer ───────────────────────────────────────────────────
    messages.append({
        "role": "user",
        "content": (
            "Now write your actual contribution for this round. "
            "Be direct and incisive. Do not explain what you found — just argue. "
            "Stay within your character's voice."
        ),
    })

    stream = await client.chat.completions.create(
        model=_MAIN_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.87,
        stream=True,
    )

    async for chunk in stream:
        token = chunk.choices[0].delta.content
        if token:
            yield {
                "type": "token",
                "agent": agent_key,
                "round": round_name,
                "text": token,
            }
