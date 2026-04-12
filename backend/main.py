import asyncio
import json
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from groq import AsyncGroq
from pydantic import BaseModel

from .agents import VOTE_SUFFIX, parse_vote
from .config import FullConfig, build_system_prompt, load_config, save_config
from .database import get_history, init_db, save_debate
from .react_agent import run_react_agent

load_dotenv()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Consilium MAGI", lifespan=lifespan)

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
    cfg = await asyncio.to_thread(load_config)
    keys = list(cfg.keys())
    results: dict[str, str] = {}

    # Pre-build prompts and max_tokens for every agent
    prompts: dict[str, str] = {}
    token_limits: dict[str, int] = {}
    for key in keys:
        p, t = build_system_prompt(key, cfg[key])
        prompts[key] = p
        token_limits[key] = t

    def label(k: str) -> str:
        return f"{cfg[k]['name'].upper()}-{'1' if k == 'MELCHIOR' else '2' if k == 'BALTHASAR' else '3'}"

    def role(k: str) -> str:
        return cfg[k]["archetype"] if cfg[k]["archetype"] != "Custom" else "MAGI"

    try:
        # ── Round 1: opening positions (ReAct loop) ───────────────────
        for key in keys:
            user_msg = f"The question before the MAGI: {topic}\n\nState your opening position."
            yield sse({"type": "agent_start", "agent": key, "round": "r1"})
            full = ""
            async for event in run_react_agent(
                client, key, "r1", prompts[key], user_msg,
                debate_context="", max_tokens=token_limits[key],
            ):
                if event["type"] == "token":
                    full += event["text"]
                yield sse(event)
            results[f"r1_{key}"] = full
            yield sse({"type": "agent_done", "agent": key, "round": "r1"})

        # ── Round 2: responses with full R1 context (ReAct loop) ──────
        r1_block = "\n\n".join(
            f"{label(k)} [{role(k)}]:\n{results[f'r1_{k}']}"
            for k in keys
        )
        for key in keys:
            user_msg = (
                f"The question: {topic}\n\n"
                f"Round 1 positions:\n{r1_block}\n\n"
                "Respond. Do not repeat your opening — advance your argument, "
                "attack theirs, or surface the contradiction between your fragments."
            )
            yield sse({"type": "agent_start", "agent": key, "round": "r2"})
            full = ""
            async for event in run_react_agent(
                client, key, "r2", prompts[key], user_msg,
                debate_context=r1_block, max_tokens=token_limits[key],
            ):
                if event["type"] == "token":
                    full += event["text"]
                yield sse(event)
            results[f"r2_{key}"] = full
            yield sse({"type": "agent_done", "agent": key, "round": "r2"})

        # ── Vote: formal judgment with full debate context ────────────
        r2_block = "\n\n".join(
            f"{label(k)} [{role(k)}] Round 2:\n{results[f'r2_{k}']}"
            for k in keys
        )
        full_debate = r1_block + "\n\n" + r2_block
        approve_count = 0
        vote_data: dict[str, dict] = {}

        for key in keys:
            yield sse({"type": "agent_start", "agent": key, "round": "vote"})
            msgs = [{
                "role": "user",
                "content": f"The question: {topic}\n\nFull deliberation:\n{full_debate}{VOTE_SUFFIX}",
            }]
            stream = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": prompts[key]}] + msgs,
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
            vote_data[key] = {"vote": vote, "reason": reason}
            yield sse({"type": "vote", "agent": key, "vote": vote, "reason": reason})

        verdict = "APPROVE" if approve_count >= 2 else "REJECT"
        yield sse({"type": "verdict", "approve_count": approve_count, "verdict": verdict})

        await save_debate(topic, verdict, approve_count, vote_data)

        # ── Split vote analysis (2-1 only, not unanimous) ─────────────
        if approve_count in (1, 2):
            dissenter = next(
                k for k in keys
                if vote_data[k]["vote"] == ("REJECT" if approve_count == 2 else "APPROVE")
            )
            yield sse({"type": "split_start", "dissenter": dissenter})
            msgs = [{
                "role": "user",
                "content": (
                    f"The vote is complete. The verdict is {verdict} ({approve_count}/3 approve). "
                    f"You cast the dissenting vote: {vote_data[dissenter]['vote']}.\n\n"
                    f"The question: {topic}\n\n"
                    "Speak directly to the other fragments. In one paragraph (120–150 words), "
                    "explain precisely what you see that they cannot, or will not, see. "
                    "Be specific to this question. Do not summarize the debate — illuminate your dissent."
                ),
            }]
            stream = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": prompts[dissenter]}] + msgs,
                max_tokens=210,
                temperature=0.9,
                stream=True,
            )
            async for chunk in stream:
                token = chunk.choices[0].delta.content
                if token:
                    yield sse({"type": "split_token", "text": token})
            yield sse({"type": "split_done"})

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


@app.get("/api/config")
async def get_config():
    return await asyncio.to_thread(load_config)


@app.post("/api/config")
async def post_config(body: dict):
    # Validate shape minimally — trust the frontend for now
    cfg: FullConfig = {}
    defaults_ref = await asyncio.to_thread(load_config)
    for key in ("MELCHIOR", "BALTHASAR", "CASPAR"):
        if key in body:
            cfg[key] = {**defaults_ref[key], **body[key]}
        else:
            cfg[key] = defaults_ref[key]
    await asyncio.to_thread(save_config, cfg)
    return {"status": "saved"}


@app.get("/api/history")
async def history():
    return await get_history()


@app.get("/api/health")
async def health():
    return {
        "status": "ONLINE",
        "system": "MAGI",
        "groq_key_set": bool(os.environ.get("GROQ_API_KEY")),
        "tavily_key_set": bool(os.environ.get("TAVILY_API_KEY")),
    }
