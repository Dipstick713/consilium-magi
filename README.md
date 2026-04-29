# CONSILIUM MAGI

> *The three MAGI are not computers. They are fragments of a woman.*

A real-time AI debate engine inspired by the MAGI supercomputer system from *Neon Genesis Evangelion*. Three agents — each a distinct fragment of Dr. Naoko Akagi's psyche — argue any question from their psychological lenses, then cast a formal 2-of-3 majority vote. You play Commander and may override.

**Stack:** React + TypeScript + Vite · TailwindCSS · FastAPI · Groq API (`llama-3.3-70b-versatile`, streaming SSE)

---

## The Fragments

| Unit | Fragment | Lens | Color |
|------|----------|------|-------|
| **MELCHIOR-1** | The Scientist | Evidence, falsifiability, causal inference — cold and precise | Amber `#FFB000` |
| **BALTHASAR-2** | The Mother | Utilitarian protection; survival of the greatest number | Green `#00FF41` |
| **CASPAR-3** | The Woman | Human dignity, desire, meaning — *but is it worth living?* | Purple `#9B59B6` |

Each agent knows the others are fragments of herself. They reference this shared origin when they disagree.

---

## Protocol

1. Submit a question
2. **Round 1** — each fragment states its opening position (streamed live)
3. **Inter-agent reactions** — after each statement, the other two fragments fire one-line agreement/challenge/synthesis callouts
4. **Round 2** — each fragment responds to the others (streamed live)
5. **Vote** — each fragment renders `APPROVE` or `REJECT` with a one-sentence reason
6. **Verdict** — 2-of-3 majority displayed
7. **Commander Override** — override the verdict in either direction; rescind at will

### Shared memory layer (SQLite)

- Stores claims by fragment and round
- Stores cited evidence (search queries, cited URLs, inline links)
- Stores past votes by fragment/topic
- Logs contradictions when a fragment flips from a relevant past vote
- Injects each fragment's relevant past votes at debate start; contradictions require explicit acknowledgment

---

## Setup

### 1. Install Python dependencies

```bash
uv sync
```

### 2. Install frontend dependencies

```bash
cd frontend && npm install
```

### 3. Configure API key

```bash
cp .env.example .env
# edit .env and set GROQ_API_KEY=gsk_...
```

Or enter the key directly in the UI — no restart needed.

### 4. Run (two terminals)

```bash
# Terminal 1 — backend
uv run uvicorn backend.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

---

## Project structure

```
consilium-magi/
├── backend/
│   ├── agents.py       # System prompts, vote parsing
│   └── main.py         # FastAPI app + SSE debate stream
├── frontend/
│   └── src/
│       ├── App.tsx             # State machine + SSE client
│       ├── types.ts            # Shared TypeScript types
│       ├── agents.ts           # Client-side agent config
│       └── components/
│           ├── Header.tsx
│           ├── TopicInput.tsx
│           ├── AgentColumn.tsx
│           └── VerdictPanel.tsx
├── pyproject.toml      # uv / Python deps
└── .env.example
```

---

## API

`POST /api/debate` — accepts `{ topic, api_key? }`, returns an SSE stream.

| Event | Payload |
|-------|---------|
| `agent_start` | `{ agent, round }` |
| `token` | `{ agent, round, text }` |
| `reaction` | `{ agent, round, reactor, stance, text }` |
| `agent_done` | `{ agent, round }` |
| `vote` | `{ agent, vote, reason }` |
| `verdict` | `{ approve_count, verdict }` |
| `done` / `error` | `{}` / `{ message }` |
