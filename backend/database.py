"""
SQLite persistence for MAGI deliberation and shared memory.
Uses asyncio.to_thread so the sync sqlite3 driver doesn't block the event loop.
"""
import asyncio
import re
import sqlite3
from pathlib import Path

DB_PATH = Path("magi_history.db")


# ── Schema ─────────────────────────────────────────────────────────────────────

_CREATE = """
CREATE TABLE IF NOT EXISTS debates (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    topic         TEXT    NOT NULL,
    verdict       TEXT    NOT NULL,
    approve_count INTEGER NOT NULL,
    melchior_vote    TEXT,
    balthasar_vote   TEXT,
    caspar_vote      TEXT,
    melchior_reason  TEXT,
    balthasar_reason TEXT,
    caspar_reason    TEXT,
    created_at    TEXT DEFAULT (strftime('%Y-%m-%d %H:%M', 'now'))
);

CREATE TABLE IF NOT EXISTS claims (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    debate_id  INTEGER NOT NULL,
    agent_key  TEXT    NOT NULL,
    round      TEXT    NOT NULL,
    claim_text TEXT    NOT NULL,
    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M', 'now')),
    FOREIGN KEY (debate_id) REFERENCES debates(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evidence (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    debate_id   INTEGER NOT NULL,
    agent_key   TEXT    NOT NULL,
    round       TEXT    NOT NULL,
    source_type TEXT    NOT NULL,
    source_ref  TEXT    NOT NULL,
    detail      TEXT,
    created_at  TEXT DEFAULT (strftime('%Y-%m-%d %H:%M', 'now')),
    FOREIGN KEY (debate_id) REFERENCES debates(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS contradictions (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    debate_id          INTEGER NOT NULL,
    agent_key          TEXT    NOT NULL,
    previous_debate_id INTEGER,
    previous_topic     TEXT,
    previous_vote      TEXT    NOT NULL,
    current_vote       TEXT    NOT NULL,
    acknowledgment     TEXT    NOT NULL,
    created_at         TEXT DEFAULT (strftime('%Y-%m-%d %H:%M', 'now')),
    FOREIGN KEY (debate_id) REFERENCES debates(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_claims_debate_agent ON claims(debate_id, agent_key);
CREATE INDEX IF NOT EXISTS idx_evidence_debate_agent ON evidence(debate_id, agent_key);
CREATE INDEX IF NOT EXISTS idx_contradictions_agent ON contradictions(agent_key, created_at DESC);
"""


# ── Internal helpers ───────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _init_sync() -> None:
    with _connect() as conn:
        conn.executescript(_CREATE)
        conn.commit()


def _vote_columns_for(agent_key: str) -> tuple[str, str]:
    key = agent_key.upper()
    if key == "MELCHIOR":
        return "melchior_vote", "melchior_reason"
    if key == "BALTHASAR":
        return "balthasar_vote", "balthasar_reason"
    if key == "CASPAR":
        return "caspar_vote", "caspar_reason"
    raise ValueError(f"Unknown agent key: {agent_key}")


def _tokenize_topic(text: str) -> set[str]:
    stopwords = {
        "about", "after", "against", "between", "could", "should", "would",
        "their", "there", "these", "those", "which", "while", "where",
        "when", "what", "this", "that", "with", "from", "into", "over",
        "under", "than", "have", "has", "were", "been", "them", "they",
        "your", "ours", "will", "shall", "must", "might", "does", "did",
    }
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {w for w in words if len(w) >= 4 and w not in stopwords}


def _topic_relevance(a: str, b: str) -> int:
    at = _tokenize_topic(a)
    bt = _tokenize_topic(b)
    if not at or not bt:
        return 0
    score = len(at.intersection(bt))
    a_norm = " ".join(a.lower().split())
    b_norm = " ".join(b.lower().split())
    if a_norm and b_norm and (a_norm in b_norm or b_norm in a_norm):
        score += 2
    return score


def _save_sync(
    topic: str,
    verdict: str,
    approve_count: int,
    votes: dict[str, dict],
    claims: list[dict],
    evidence: list[dict],
    contradictions: list[dict],
) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO debates (
                topic, verdict, approve_count,
                melchior_vote, balthasar_vote, caspar_vote,
                melchior_reason, balthasar_reason, caspar_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                topic, verdict, approve_count,
                votes.get("MELCHIOR",  {}).get("vote"),
                votes.get("BALTHASAR", {}).get("vote"),
                votes.get("CASPAR",    {}).get("vote"),
                votes.get("MELCHIOR",  {}).get("reason"),
                votes.get("BALTHASAR", {}).get("reason"),
                votes.get("CASPAR",    {}).get("reason"),
            ),
        )
        debate_id = int(cur.lastrowid)

        if claims:
            conn.executemany(
                """
                INSERT INTO claims (debate_id, agent_key, round, claim_text)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        debate_id,
                        item.get("agent_key", ""),
                        item.get("round", ""),
                        item.get("claim_text", ""),
                    )
                    for item in claims
                    if item.get("agent_key") and item.get("round") and item.get("claim_text")
                ],
            )

        if evidence:
            conn.executemany(
                """
                INSERT INTO evidence (debate_id, agent_key, round, source_type, source_ref, detail)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        debate_id,
                        item.get("agent_key", ""),
                        item.get("round", ""),
                        item.get("source_type", ""),
                        item.get("source_ref", ""),
                        item.get("detail", ""),
                    )
                    for item in evidence
                    if item.get("agent_key") and item.get("round") and item.get("source_type") and item.get("source_ref")
                ],
            )

        if contradictions:
            conn.executemany(
                """
                INSERT INTO contradictions (
                    debate_id, agent_key, previous_debate_id, previous_topic,
                    previous_vote, current_vote, acknowledgment
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        debate_id,
                        item.get("agent_key", ""),
                        item.get("previous_debate_id"),
                        item.get("previous_topic", ""),
                        item.get("previous_vote", ""),
                        item.get("current_vote", ""),
                        item.get("acknowledgment", ""),
                    )
                    for item in contradictions
                    if item.get("agent_key") and item.get("previous_vote")
                    and item.get("current_vote") and item.get("acknowledgment")
                ],
            )

        conn.commit()
        return debate_id


def _fetch_sync(limit: int) -> list[dict]:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT * FROM debates ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]


def _fetch_agent_vote_memory_sync(topic: str, agent_key: str, limit: int) -> list[dict]:
    vote_col, reason_col = _vote_columns_for(agent_key)
    query = f"""
        SELECT
            id,
            topic,
            verdict,
            approve_count,
            {vote_col}  AS vote,
            {reason_col} AS reason,
            created_at
        FROM debates
        WHERE {vote_col} IS NOT NULL
        ORDER BY id DESC
        LIMIT 100
    """
    with _connect() as conn:
        rows = [dict(row) for row in conn.execute(query).fetchall()]

    scored: list[dict] = []
    for row in rows:
        relevance = _topic_relevance(topic, row["topic"])
        if relevance <= 0:
            continue
        row["relevance"] = relevance
        scored.append(row)

    scored.sort(key=lambda r: (int(r["relevance"]), int(r["id"])), reverse=True)
    return scored[:limit]


# ── Public async API ───────────────────────────────────────────────────────────

async def init_db() -> None:
    await asyncio.to_thread(_init_sync)


async def save_debate(
    topic: str,
    verdict: str,
    approve_count: int,
    votes: dict[str, dict],
    claims: list[dict] | None = None,
    evidence: list[dict] | None = None,
    contradictions: list[dict] | None = None,
) -> int:
    return await asyncio.to_thread(
        _save_sync,
        topic,
        verdict,
        approve_count,
        votes,
        claims or [],
        evidence or [],
        contradictions or [],
    )


async def get_history(limit: int = 100) -> list[dict]:
    return await asyncio.to_thread(_fetch_sync, limit)


async def get_agent_vote_memory(topic: str, agent_key: str, limit: int = 4) -> list[dict]:
    return await asyncio.to_thread(_fetch_agent_vote_memory_sync, topic, agent_key, limit)
