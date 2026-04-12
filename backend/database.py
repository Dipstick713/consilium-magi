"""
SQLite persistence for MAGI deliberation history.
Uses asyncio.to_thread so the sync sqlite3 driver doesn't block the event loop.
"""
import asyncio
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
)
"""


# ── Internal helpers ───────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_sync() -> None:
    with _connect() as conn:
        conn.execute(_CREATE)
        conn.commit()


def _save_sync(
    topic: str,
    verdict: str,
    approve_count: int,
    votes: dict[str, dict],
) -> None:
    with _connect() as conn:
        conn.execute(
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
        conn.commit()


def _fetch_sync(limit: int) -> list[dict]:
    with _connect() as conn:
        cur = conn.execute(
            "SELECT * FROM debates ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]


# ── Public async API ───────────────────────────────────────────────────────────

async def init_db() -> None:
    await asyncio.to_thread(_init_sync)


async def save_debate(
    topic: str,
    verdict: str,
    approve_count: int,
    votes: dict[str, dict],
) -> None:
    await asyncio.to_thread(_save_sync, topic, verdict, approve_count, votes)


async def get_history(limit: int = 100) -> list[dict]:
    return await asyncio.to_thread(_fetch_sync, limit)
