import json
import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from groq import AsyncGroq
from pydantic import BaseModel

from .agents import AGENTS, VOTE_SUFFIX, parse_vote

load_dotenv()

app = FastAPI(title="Consilium MAGI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


class DebateRequest(BaseModel):
    topic: str
    api_key: str = ""


def sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


async def debate_stream(topic: str, api_key: str) -> AsyncGenerator[str, None]:
    client = AsyncGroq(api_key=api_key)
    keys = list(AGENTS.keys())
    results: dict[str, str] = {}

    try:
        # ── Round 1: opening positions ────────────────────────────────
        for key in keys:
            yield sse({"type": "agent_start", "agent": key, "round": "r1"})
            msgs = [{"role": "user", "content": f"The question before the MAGI: {topic}\n\nState your opening position."}]
            stream = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": AGENTS[key]["system"]}] + msgs,
                max_tokens=220,
                temperature=0.87,
                stream=True,
            )
            full = ""
            async for chunk in stream:
                token = chunk.choices[0].delta.content
                if token:
                    full += token
                    yield sse({"type": "token", "agent": key, "round": "r1", "text": token})
            results[f"r1_{key}"] = full
            yield sse({"type": "agent_done", "agent": key, "round": "r1"})

        # ── Round 2: responses with full R1 context ───────────────────
        r1_block = "\n\n".join(
            f"{AGENTS[k]['id']} [{AGENTS[k]['role']}]:\n{results[f'r1_{k}']}"
            for k in keys
        )
        for key in keys:
            yield sse({"type": "agent_start", "agent": key, "round": "r2"})
            msgs = [{
                "role": "user",
                "content": (
                    f"The question: {topic}\n\n"
                    f"Round 1 positions:\n{r1_block}\n\n"
                    "Respond. Do not repeat your opening — advance your argument, "
                    "attack theirs, or surface the contradiction between your fragments."
                ),
            }]
            stream = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": AGENTS[key]["system"]}] + msgs,
                max_tokens=220,
                temperature=0.87,
                stream=True,
            )
            full = ""
            async for chunk in stream:
                token = chunk.choices[0].delta.content
                if token:
                    full += token
                    yield sse({"type": "token", "agent": key, "round": "r2", "text": token})
            results[f"r2_{key}"] = full
            yield sse({"type": "agent_done", "agent": key, "round": "r2"})

        # ── Vote: formal judgment with full debate context ────────────
        r2_block = "\n\n".join(
            f"{AGENTS[k]['id']} [{AGENTS[k]['role']}] Round 2:\n{results[f'r2_{k}']}"
            for k in keys
        )
        full_debate = r1_block + "\n\n" + r2_block
        approve_count = 0

        for key in keys:
            yield sse({"type": "agent_start", "agent": key, "round": "vote"})
            msgs = [{
                "role": "user",
                "content": f"The question: {topic}\n\nFull deliberation:\n{full_debate}{VOTE_SUFFIX}",
            }]
            stream = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": AGENTS[key]["system"]}] + msgs,
                max_tokens=170,
                temperature=0.87,
                stream=True,
            )
            full = ""
            async for chunk in stream:
                token = chunk.choices[0].delta.content
                if token:
                    full += token
                    yield sse({"type": "token", "agent": key, "round": "vote", "text": token})
            yield sse({"type": "agent_done", "agent": key, "round": "vote"})

            vote, reason = parse_vote(full)
            if vote == "APPROVE":
                approve_count += 1
            yield sse({"type": "vote", "agent": key, "vote": vote, "reason": reason})

        verdict = "APPROVE" if approve_count >= 2 else "REJECT"
        yield sse({"type": "verdict", "approve_count": approve_count, "verdict": verdict})
        yield sse({"type": "done"})

    except Exception as exc:
        yield sse({"type": "error", "message": str(exc)})


@app.post("/api/debate")
async def debate(request: DebateRequest):
    api_key = request.api_key or os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="No API key provided. Set GROQ_API_KEY or enter it in the UI.")
    return StreamingResponse(
        debate_stream(request.topic, api_key),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/health")
async def health():
    env_key_set = bool(os.environ.get("GROQ_API_KEY"))
    return {"status": "ONLINE", "system": "MAGI", "env_key_set": env_key_set}
