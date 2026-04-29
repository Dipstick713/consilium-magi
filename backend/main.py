import asyncio
import json
import os
import re
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
from .database import get_agent_vote_memory, get_history, init_db, save_debate
from .react_agent import run_react_agent

load_dotenv()

_REACTION_MODEL = "llama-3.1-8b-instant"
_ACK_RE = re.compile(r"ACKNOWLEDGMENT:\s*(.+)", re.IGNORECASE)


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


def _extract_claims(text: str, max_claims: int = 3) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    claims: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", normalized):
        s = sentence.strip()
        if len(s) < 45:
            continue
        if s not in claims:
            claims.append(s[:320])
        if len(claims) >= max_claims:
            break
    return claims


def _extract_urls(text: str) -> list[str]:
    raw = re.findall(r"https?://[^\s)\]>]+", text)
    urls: list[str] = []
    for item in raw:
        cleaned = item.rstrip(".,;:")
        if cleaned not in urls:
            urls.append(cleaned)
    return urls


def _memory_block(rows: list[dict]) -> str:
    if not rows:
        return "No relevant prior votes found."
    return "\n".join(
        f"- [{row['created_at']}] {row['topic']} -> {row['vote']}"
        + (f" | Reason: {row['reason']}" if row.get("reason") else "")
        for row in rows
    )


def _extract_acknowledgment(text: str) -> str | None:
    match = _ACK_RE.search(text)
    if not match:
        return None
    return f"ACKNOWLEDGMENT: {match.group(1).strip()}"


def _forced_ack(conflict: dict, current_vote: str) -> str:
    previous_vote = conflict.get("vote", "UNKNOWN")
    previous_topic = conflict.get("topic", "a related topic")
    return (
        f"ACKNOWLEDGMENT: I previously voted {previous_vote} on \"{previous_topic}\"; "
        f"I now vote {current_vote} because this case changes the balance of evidence."
    )


def _parse_reaction(content: str) -> tuple[str, str]:
    stance_match = re.search(r"STANCE:\s*(agreement|challenge|synthesis)", content, re.IGNORECASE)
    line_match = re.search(r"LINE:\s*(.+)", content, re.IGNORECASE)
    stance = (stance_match.group(1).lower() if stance_match else "challenge")
    line = (line_match.group(1).strip() if line_match else "I challenge this framing.")
    words = line.split()
    if len(words) > 14:
        line = " ".join(words[:14]).rstrip(".,;:") + "."
    return stance, line.strip()


async def _generate_reaction(
    client: AsyncGroq,
    cfg: FullConfig,
    topic: str,
    speaker_key: str,
    reactor_key: str,
    round_name: str,
    speaker_text: str,
) -> dict:
    reactor_name = cfg[reactor_key]["name"].strip().title()
    speaker_name = cfg[speaker_key]["name"].strip().title()
    prompt = (
        f"Debate topic: {topic}\n"
        f"Round: {round_name}\n"
        f"{speaker_name}'s statement:\n{speaker_text[:320]}\n\n"
        "Return EXACTLY two lines:\n"
        "STANCE: agreement|challenge|synthesis\n"
        "LINE: <one sentence, <=14 words, no name prefix>"
    )
    try:
        resp = await client.chat.completions.create(
            model=_REACTION_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are {reactor_name}. React quickly to another MAGI fragment. "
                        "Use sharp, direct language."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=30,
            temperature=0.6,
        )
        raw = resp.choices[0].message.content or ""
    except Exception:
        raw = "STANCE: challenge\nLINE: I cannot accept this conclusion yet."

    stance, line = _parse_reaction(raw)
    return {
        "reactor": reactor_key,
        "stance": stance,
        "text": f"{reactor_name}: {line}",
    }


async def _emit_reactions(
    client: AsyncGroq,
    cfg: FullConfig,
    topic: str,
    speaker_key: str,
    round_name: str,
    speaker_text: str,
) -> list[dict]:
    reactors = [k for k in cfg.keys() if k != speaker_key]
    tasks = [
        _generate_reaction(client, cfg, topic, speaker_key, reactor, round_name, speaker_text)
        for reactor in reactors
    ]
    return await asyncio.gather(*tasks)


async def debate_stream(topic: str, api_key: str) -> AsyncGenerator[str, None]:
    client = AsyncGroq(api_key=api_key)
    cfg = await asyncio.to_thread(load_config)
    keys = list(cfg.keys())
    results: dict[str, str] = {}
    claims: list[dict] = []
    evidence: list[dict] = []
    contradictions: list[dict] = []
    vote_memory: dict[str, list[dict]] = {}

    # Pre-build prompts and max_tokens for every agent
    prompts: dict[str, str] = {}
    token_limits: dict[str, int] = {}
    for key in keys:
        p, t = build_system_prompt(key, cfg[key])
        prompts[key] = p
        token_limits[key] = t
        vote_memory[key] = await get_agent_vote_memory(topic, key, limit=4)

    def label(k: str) -> str:
        return f"{cfg[k]['name'].upper()}-{'1' if k == 'MELCHIOR' else '2' if k == 'BALTHASAR' else '3'}"

    def role(k: str) -> str:
        return cfg[k]["archetype"] if cfg[k]["archetype"] != "Custom" else "MAGI"

    try:
        # ── Round 1: opening positions (ReAct loop) ───────────────────
        for key in keys:
            memory = _memory_block(vote_memory[key])
            user_msg = (
                f"The question before the MAGI: {topic}\n\n"
                f"Shared memory — your relevant past votes:\n{memory}\n\n"
                "State your opening position. If your stance departs from relevant past votes, "
                "acknowledge that shift explicitly."
            )
            yield sse({"type": "agent_start", "agent": key, "round": "r1"})
            full = ""
            async for event in run_react_agent(
                client, key, "r1", prompts[key], user_msg,
                debate_context="", max_tokens=token_limits[key],
            ):
                if event["type"] == "token":
                    full += event["text"]
                if event["type"] == "trace_action":
                    tool = event.get("tool")
                    args = event.get("args") or {}
                    if tool == "web_search" and args.get("query"):
                        evidence.append({
                            "agent_key": key,
                            "round": "r1",
                            "source_type": "web_search",
                            "source_ref": str(args["query"]),
                            "detail": "",
                        })
                    if tool == "cite_source" and args.get("url"):
                        evidence.append({
                            "agent_key": key,
                            "round": "r1",
                            "source_type": "cite_source",
                            "source_ref": str(args["url"]),
                            "detail": "",
                        })
                yield sse(event)
            results[f"r1_{key}"] = full
            for claim in _extract_claims(full):
                claims.append({"agent_key": key, "round": "r1", "claim_text": claim})
            for url in _extract_urls(full):
                evidence.append({
                    "agent_key": key,
                    "round": "r1",
                    "source_type": "inline_url",
                    "source_ref": url,
                    "detail": "",
                })
            yield sse({"type": "agent_done", "agent": key, "round": "r1"})
            reactions = await _emit_reactions(client, cfg, topic, key, "r1", full)
            for reaction in reactions:
                yield sse({
                    "type": "reaction",
                    "agent": key,
                    "round": "r1",
                    "reactor": reaction["reactor"],
                    "stance": reaction["stance"],
                    "text": reaction["text"],
                })

        # ── Round 2: responses with full R1 context (ReAct loop) ──────
        r1_block = "\n\n".join(
            f"{label(k)} [{role(k)}]:\n{results[f'r1_{k}']}"
            for k in keys
        )
        for key in keys:
            memory = _memory_block(vote_memory[key])
            user_msg = (
                f"The question: {topic}\n\n"
                f"Shared memory — your relevant past votes:\n{memory}\n\n"
                f"Round 1 positions:\n{r1_block}\n\n"
                "Respond. Do not repeat your opening — advance your argument, "
                "attack theirs, or surface the contradiction between your fragments. "
                "If you diverge from relevant past votes, acknowledge it explicitly."
            )
            yield sse({"type": "agent_start", "agent": key, "round": "r2"})
            full = ""
            async for event in run_react_agent(
                client, key, "r2", prompts[key], user_msg,
                debate_context=r1_block, max_tokens=token_limits[key],
            ):
                if event["type"] == "token":
                    full += event["text"]
                if event["type"] == "trace_action":
                    tool = event.get("tool")
                    args = event.get("args") or {}
                    if tool == "web_search" and args.get("query"):
                        evidence.append({
                            "agent_key": key,
                            "round": "r2",
                            "source_type": "web_search",
                            "source_ref": str(args["query"]),
                            "detail": "",
                        })
                    if tool == "cite_source" and args.get("url"):
                        evidence.append({
                            "agent_key": key,
                            "round": "r2",
                            "source_type": "cite_source",
                            "source_ref": str(args["url"]),
                            "detail": "",
                        })
                yield sse(event)
            results[f"r2_{key}"] = full
            for claim in _extract_claims(full):
                claims.append({"agent_key": key, "round": "r2", "claim_text": claim})
            for url in _extract_urls(full):
                evidence.append({
                    "agent_key": key,
                    "round": "r2",
                    "source_type": "inline_url",
                    "source_ref": url,
                    "detail": "",
                })
            yield sse({"type": "agent_done", "agent": key, "round": "r2"})
            reactions = await _emit_reactions(client, cfg, topic, key, "r2", full)
            for reaction in reactions:
                yield sse({
                    "type": "reaction",
                    "agent": key,
                    "round": "r2",
                    "reactor": reaction["reactor"],
                    "stance": reaction["stance"],
                    "text": reaction["text"],
                })

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
            memory = _memory_block(vote_memory[key])
            msgs = [{
                "role": "user",
                "content": (
                    f"The question: {topic}\n\n"
                    f"Shared memory — your relevant past votes:\n{memory}\n\n"
                    "If your current vote contradicts a relevant past vote, include a line "
                    "starting with 'ACKNOWLEDGMENT:' before the vote format.\n\n"
                    f"Full deliberation:\n{full_debate}{VOTE_SUFFIX}"
                ),
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

            vote, reason = parse_vote(full)
            conflict = next((row for row in vote_memory[key] if row.get("vote") and row["vote"] != vote), None)
            acknowledgment = _extract_acknowledgment(full)
            if conflict:
                if not acknowledgment:
                    acknowledgment = _forced_ack(conflict, vote)
                    full += f"\n{acknowledgment}"
                    yield sse({"type": "token", "agent": key, "round": "vote", "text": f"\n{acknowledgment}"})
                contradictions.append({
                    "agent_key": key,
                    "previous_debate_id": conflict.get("id"),
                    "previous_topic": conflict.get("topic", ""),
                    "previous_vote": conflict.get("vote", ""),
                    "current_vote": vote,
                    "acknowledgment": acknowledgment,
                })

            claims.append({
                "agent_key": key,
                "round": "vote",
                "claim_text": f"Vote rationale: {reason}",
            })
            yield sse({"type": "agent_done", "agent": key, "round": "vote"})

            if vote == "APPROVE":
                approve_count += 1
            vote_data[key] = {"vote": vote, "reason": reason}
            yield sse({"type": "vote", "agent": key, "vote": vote, "reason": reason})

        verdict = "APPROVE" if approve_count >= 2 else "REJECT"
        yield sse({"type": "verdict", "approve_count": approve_count, "verdict": verdict})

        await save_debate(
            topic,
            verdict,
            approve_count,
            vote_data,
            claims=claims,
            evidence=evidence,
            contradictions=contradictions,
        )

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
