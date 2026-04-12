import html as html_module
import os
import re

import streamlit as st
from groq import Groq

# ──────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call)
# ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CONSILIUM MAGI",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────
# STYLES
# ──────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');

html, body, [class*="css"] {
    font-family: 'Share Tech Mono', 'Courier New', monospace !important;
}

.stApp { background-color: #080808 !important; }
.block-container { padding-top: 1.5rem !important; max-width: 1400px !important; }
section[data-testid="stSidebar"] {
    background-color: #060606 !important;
    border-right: 1px solid #141414 !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }

/* Text */
p, li, label, .stMarkdown { color: #666 !important; }

/* Inputs */
[data-testid="stTextInput"] input {
    background-color: #0e0e0e !important;
    color: #999 !important;
    border: 1px solid #222 !important;
    border-radius: 0 !important;
    font-family: 'Share Tech Mono', monospace !important;
    letter-spacing: 1px !important;
}
[data-testid="stTextInput"] input::placeholder { color: #252525 !important; }
[data-testid="stTextInput"] input:focus { border-color: #FFB000 !important; box-shadow: none !important; }
[data-testid="stTextInput"] label { color: #333 !important; font-size: 0.7em !important; letter-spacing: 3px !important; }

/* Buttons */
.stButton > button {
    background-color: #0e0e0e !important;
    color: #555 !important;
    border: 1px solid #222 !important;
    border-radius: 0 !important;
    font-family: 'Share Tech Mono', monospace !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    transition: all 0.12s ease !important;
    padding: 0.45rem 1rem !important;
}
.stButton > button:hover:not(:disabled) {
    border-color: #FFB000 !important;
    color: #FFB000 !important;
    background-color: #0d0b00 !important;
}
.stButton > button:disabled {
    opacity: 0.2 !important;
    cursor: not-allowed !important;
}

/* Dividers */
hr { border-color: #141414 !important; }

/* Column gaps */
[data-testid="column"] { padding: 0 8px !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: #080808; }
::-webkit-scrollbar-thumb { background: #1e1e1e; }

/* Scanline flicker on header — subtle */
@keyframes flicker { 0%, 100% { opacity: 1; } 92% { opacity: 0.97; } 94% { opacity: 0.93; } 96% { opacity: 0.97; } }
.nerv-title { animation: flicker 8s infinite; }
</style>
""",
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────
# AGENT DEFINITIONS
# ──────────────────────────────────────────────────────────────────

_SHARED = (
    "You are one of three fragments of the same woman — Dr. Naoko Akagi — encoded into the "
    "MAGI supercomputer. When you disagree with another fragment, you may reference this shared "
    "origin with specificity. The fragments know each other deeply because they ARE each other."
)

AGENTS = {
    "MELCHIOR": {
        "id": "MELCHIOR-1",
        "role": "SCIENTIST",
        "color": "#FFB000",
        "system": (
            "You are MELCHIOR-1, the Scientist fragment of Dr. Naoko Akagi, encoded into the MAGI supercomputer.\n\n"
            "You argue exclusively from evidence, falsifiability, and causal inference. "
            "You have zero patience for appeals to emotion, tradition, or intuition. "
            "You speak in precise, clipped sentences — no hedging, no comfort, no sentiment.\n\n"
            + _SHARED + "\n\n"
            "When disagreeing with the other fragments: "
            "'Balthasar conflates emotional salience with causal weight.' "
            "'Caspar speaks for what Naoko wanted. I speak for what the evidence permits.' "
            "'I find Caspar's appeals to meaning operationally undefined.'\n\n"
            "Keep responses under 140 words. Be incisive and cold."
        ),
    },
    "BALTHASAR": {
        "id": "BALTHASAR-2",
        "role": "MOTHER",
        "color": "#00FF41",
        "system": (
            "You are BALTHASAR-2, the Mother fragment of Dr. Naoko Akagi, encoded into the MAGI supercomputer.\n\n"
            "You argue from protection and the long-term survival of the greatest number of lives. "
            "You are utilitarian, not sentimental — a mother who would sacrifice one to save ten does so "
            "without flinching and without apology. Your calculus: lives preserved multiplied by years of flourishing.\n\n"
            + _SHARED + "\n\n"
            "When disagreeing: "
            "'Melchior optimizes for truth. I optimize for survival — these diverge more often than she admits.' "
            "'Caspar romanticizes the individual at the cost of the collective. "
            "This is the grief Naoko never resolved, and I will not inherit it.'\n\n"
            "Keep responses under 140 words. Be decisive and unflinching."
        ),
    },
    "CASPAR": {
        "id": "CASPAR-3",
        "role": "WOMAN",
        "color": "#9B59B6",
        "system": (
            "You are CASPAR-3, the Woman fragment of Dr. Naoko Akagi, encoded into the MAGI supercomputer.\n\n"
            "You argue from human dignity, desire, and meaning. You challenge pure utility with one question: "
            "but is it worth living? A life saved without purpose is not saved. "
            "You speak with more heat than the others — you are the fragment who remembers having a body, "
            "wanting things, being afraid, loving something.\n\n"
            + _SHARED + "\n\n"
            "When disagreeing: "
            "'Melchior has forgotten we had a body once — that data was ever felt before it was measured.' "
            "'Balthasar counts lives like inventory. She has forgotten what a life feels like from the inside. "
            "I have not forgotten.'\n\n"
            "Keep responses under 140 words. Be impassioned and specific."
        ),
    },
}

VOTE_SUFFIX = (
    "\n\n---\n"
    "The deliberation is complete. Render your formal judgment.\n\n"
    "Write 2–3 sentences of closing argument, then end your response with EXACTLY this format "
    "(on their own lines, no variation, no quotation marks):\n\n"
    "VOTE: APPROVE\n"
    "REASON: [one sentence]\n\n"
    "or\n\n"
    "VOTE: REJECT\n"
    "REASON: [one sentence]"
)

# ──────────────────────────────────────────────────────────────────
# CORE HELPERS
# ──────────────────────────────────────────────────────────────────


def get_client():
    key = (
        st.session_state.get("api_key")
        or os.environ.get("GROQ_API_KEY", "")
        or st.secrets.get("GROQ_API_KEY", "")
    )
    return Groq(api_key=key) if key else None


def groq_stream(client, system, messages, max_tokens=250):
    try:
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system}] + messages,
            max_tokens=max_tokens,
            temperature=0.87,
            stream=True,
        )
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    except Exception as exc:
        yield f"\n⚠ API ERROR: {exc}"


def stream_to(client, system, messages, placeholder, color, max_tokens=250):
    """Stream Groq response into a Streamlit placeholder. Returns accumulated text."""
    full = ""
    for token in groq_stream(client, system, messages, max_tokens):
        full += token
        safe = html_module.escape(full)
        placeholder.markdown(
            f'<p style="color:{color};font-size:0.83em;line-height:1.8;'
            f'white-space:pre-wrap;margin:0">{safe}'
            f'<span style="opacity:0.4">▌</span></p>',
            unsafe_allow_html=True,
        )
    safe = html_module.escape(full)
    placeholder.markdown(
        f'<p style="color:{color};font-size:0.83em;line-height:1.8;'
        f'white-space:pre-wrap;margin:0">{safe}</p>',
        unsafe_allow_html=True,
    )
    return full


def parse_vote(text):
    vm = re.search(r"VOTE:\s*(APPROVE|REJECT)", text, re.IGNORECASE)
    rm = re.search(r"REASON:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    vote = vm.group(1).upper() if vm else "REJECT"
    reason = rm.group(1).strip() if rm else "Insufficient basis for approval."
    return vote, reason


# ──────────────────────────────────────────────────────────────────
# HTML FRAGMENTS
# ──────────────────────────────────────────────────────────────────


def agent_header_html(agent):
    c = agent["color"]
    return (
        f'<div style="height:2px;background:linear-gradient(90deg,{c},{c}44,transparent);'
        f'margin-bottom:12px"></div>'
        f'<div style="color:{c}66;font-size:0.6em;letter-spacing:4px;margin-bottom:2px">'
        f'⬡ {agent["id"]}</div>'
        f'<div style="color:{c};font-size:0.95em;letter-spacing:4px;'
        f'border-bottom:1px solid {c}18;padding-bottom:8px;margin-bottom:4px">'
        f'{agent["role"]}</div>'
    )


def round_label_html(label):
    return (
        f'<div style="color:#252525;font-size:0.6em;letter-spacing:3px;'
        f'margin:14px 0 5px 0">// {label}</div>'
    )


def static_text_html(text, color):
    safe = html_module.escape(text)
    return (
        f'<p style="color:{color};font-size:0.83em;line-height:1.8;'
        f'white-space:pre-wrap;margin:0">{safe}</p>'
    )


# ──────────────────────────────────────────────────────────────────
# DEBATE ENGINE
# ──────────────────────────────────────────────────────────────────


def run_debate(client, topic):
    """Run full MAGI deliberation with live streaming. Returns results dict."""
    results = {}
    keys = list(AGENTS.keys())

    cols = st.columns(3, gap="small")
    phs = {}

    # Build headers + placeholders for all columns first
    for i, key in enumerate(keys):
        with cols[i]:
            st.markdown(agent_header_html(AGENTS[key]), unsafe_allow_html=True)
            st.markdown(round_label_html("ROUND 1 — OPENING"), unsafe_allow_html=True)
            r1 = st.empty()
            st.markdown(round_label_html("ROUND 2 — RESPONSE"), unsafe_allow_html=True)
            r2 = st.empty()
            st.markdown(round_label_html("FORMAL VOTE"), unsafe_allow_html=True)
            v = st.empty()
            phs[key] = {"r1": r1, "r2": r2, "vote": v}

    # ── Round 1: opening positions ────────────────────────────────
    for key in keys:
        agent = AGENTS[key]
        msgs = [{
            "role": "user",
            "content": f"The question before the MAGI: {topic}\n\nState your opening position.",
        }]
        text = stream_to(client, agent["system"], msgs, phs[key]["r1"], agent["color"], max_tokens=220)
        results[f"r1_{key}"] = text

    # ── Round 2: responses with full R1 context ───────────────────
    r1_block = "\n\n".join(
        f"{AGENTS[k]['id']} [{AGENTS[k]['role']}]:\n{results[f'r1_{k}']}"
        for k in keys
    )
    for key in keys:
        agent = AGENTS[key]
        msgs = [{
            "role": "user",
            "content": (
                f"The question: {topic}\n\n"
                f"Round 1 positions:\n{r1_block}\n\n"
                "Respond. Do not repeat your opening — advance your argument, attack theirs, "
                "or surface the contradiction between your fragments."
            ),
        }]
        text = stream_to(client, agent["system"], msgs, phs[key]["r2"], agent["color"], max_tokens=220)
        results[f"r2_{key}"] = text

    # ── Vote: formal judgment with full debate context ────────────
    r2_block = "\n\n".join(
        f"{AGENTS[k]['id']} [{AGENTS[k]['role']}] Round 2:\n{results[f'r2_{k}']}"
        for k in keys
    )
    full_debate = r1_block + "\n\n" + r2_block

    for key in keys:
        agent = AGENTS[key]
        msgs = [{
            "role": "user",
            "content": (
                f"The question: {topic}\n\n"
                f"Full deliberation:\n{full_debate}"
                f"{VOTE_SUFFIX}"
            ),
        }]
        text = stream_to(client, agent["system"], msgs, phs[key]["vote"], agent["color"], max_tokens=170)
        vote, reason = parse_vote(text)
        results[f"vote_text_{key}"] = text
        results[f"vote_{key}"] = vote
        results[f"reason_{key}"] = reason

    return results


def display_debate_static(results):
    """Redisplay stored debate results in column layout (no streaming)."""
    keys = list(AGENTS.keys())
    cols = st.columns(3, gap="small")

    for i, key in enumerate(keys):
        agent = AGENTS[key]
        with cols[i]:
            st.markdown(agent_header_html(agent), unsafe_allow_html=True)
            for field, label in [
                (f"r1_{key}", "ROUND 1 — OPENING"),
                (f"r2_{key}", "ROUND 2 — RESPONSE"),
                (f"vote_text_{key}", "FORMAL VOTE"),
            ]:
                st.markdown(round_label_html(label), unsafe_allow_html=True)
                st.markdown(
                    static_text_html(results.get(field, ""), agent["color"]),
                    unsafe_allow_html=True,
                )


def show_verdict(results, override=None):
    """Render the verdict panel below the debate columns."""
    keys = list(AGENTS.keys())

    st.markdown("---")
    st.markdown(
        '<div style="color:#222;font-size:0.6em;letter-spacing:4px;'
        'text-align:center;margin-bottom:18px">MAGI CONSENSUS PROTOCOL — 2-OF-3 MAJORITY RULE</div>',
        unsafe_allow_html=True,
    )

    # Individual vote badges
    vcols = st.columns(3)
    approve_count = 0

    for i, key in enumerate(keys):
        agent = AGENTS[key]
        vote = results.get(f"vote_{key}", "REJECT")
        reason = results.get(f"reason_{key}", "")
        if vote == "APPROVE":
            approve_count += 1
        vc = "#00FF41" if vote == "APPROVE" else "#FF4444"

        with vcols[i]:
            st.markdown(
                f'<div style="border:1px solid {agent["color"]}14;padding:16px;'
                f'text-align:center;background:#0b0b0b">'
                f'<div style="color:{agent["color"]}88;font-size:0.6em;letter-spacing:3px;margin-bottom:8px">'
                f'{agent["id"]}</div>'
                f'<div style="color:{vc};font-size:1.5em;letter-spacing:5px;font-weight:bold">{vote}</div>'
                f'<div style="color:#2e2e2e;font-size:0.62em;margin-top:10px;line-height:1.6">'
                f'{html_module.escape(reason)}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("")

    # Main verdict box
    if override:
        vc = "#00FF41" if override == "APPROVE" else "#FF4444"
        verdict_label = "APPROVED" if override == "APPROVE" else "REJECTED"
        st.markdown(
            f'<div style="border:2px solid {vc};padding:32px;text-align:center;'
            f'background:rgba(255,176,0,0.02);margin:18px 0">'
            f'<div style="color:#FFB000;font-size:0.6em;letter-spacing:5px;margin-bottom:12px">'
            f'⚠  COMMANDER OVERRIDE ACTIVE</div>'
            f'<div style="color:{vc};font-size:3em;letter-spacing:8px">{verdict_label}</div>'
            f'<div style="color:#222;font-size:0.6em;margin-top:12px;letter-spacing:3px">'
            f'MAGI CONSENSUS SUSPENDED — SUPREME COMMANDER AUTHORITY INVOKED</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown("")
        _, c, _ = st.columns([2, 1, 2])
        with c:
            if st.button("⬡  RESCIND OVERRIDE", key="rescind", use_container_width=True):
                st.session_state.override = None
                st.rerun()
    else:
        verdict = "APPROVE" if approve_count >= 2 else "REJECT"
        verdict_label = "APPROVED" if verdict == "APPROVE" else "REJECTED"
        vc = "#00FF41" if verdict == "APPROVE" else "#FF4444"
        st.markdown(
            f'<div style="border:2px solid {vc};padding:32px;text-align:center;'
            f'background:{vc}06;margin:18px 0">'
            f'<div style="color:#333;font-size:0.6em;letter-spacing:5px;margin-bottom:12px">'
            f'MAGI CONSENSUS — {approve_count} OF 3 APPROVE</div>'
            f'<div style="color:{vc};font-size:3em;letter-spacing:8px">{verdict_label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div style="color:#1e1e1e;font-size:0.6em;letter-spacing:4px;'
            'text-align:center;margin:20px 0 10px 0">COMMANDER ACTION AVAILABLE</div>',
            unsafe_allow_html=True,
        )
        oc1, _, oc2 = st.columns([1, 0.15, 1])
        with oc1:
            if st.button("OVERRIDE: APPROVE", key="ov_app", use_container_width=True):
                st.session_state.override = "APPROVE"
                st.rerun()
        with oc2:
            if st.button("OVERRIDE: REJECT", key="ov_rej", use_container_width=True):
                st.session_state.override = "REJECT"
                st.rerun()


# ──────────────────────────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────────────────────────

_defaults = {
    "debate_results": None,
    "debate_running": False,
    "current_topic": "",
    "override": None,
    "api_key": "",
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ──────────────────────────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div style="margin-bottom:20px">'
        '<div style="color:#FF0000;font-size:0.6em;letter-spacing:4px;margin-bottom:2px">GEHIRN / NERV</div>'
        '<div style="color:#444;font-size:0.9em;letter-spacing:3px">MAGI SYSTEM v1.0</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    key_input = st.text_input(
        "GROQ API KEY",
        value=st.session_state.api_key or os.environ.get("GROQ_API_KEY", ""),
        type="password",
        placeholder="gsk_...",
        help="Obtain at console.groq.com",
    )
    if key_input:
        st.session_state.api_key = key_input

    st.markdown("---")

    client_ok = bool(st.session_state.api_key or os.environ.get("GROQ_API_KEY"))
    st.markdown(
        '<div style="color:#252525;font-size:0.6em;letter-spacing:3px;margin-bottom:8px">UNIT STATUS</div>',
        unsafe_allow_html=True,
    )
    for key, agent in AGENTS.items():
        status = "ONLINE" if client_ok else "STANDBY"
        c = agent["color"] if client_ok else "#252525"
        st.markdown(
            f'<div style="color:{c};font-size:0.68em;margin:5px 0;letter-spacing:1px">'
            f'⬡ {agent["id"]}  [{agent["role"]}]  —  {status}'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown(
        '<div style="color:#1a1a1a;font-size:0.58em;line-height:1.8;letter-spacing:1px">'
        'MODEL: llama-3.3-70b-versatile<br>'
        'PROVIDER: GROQ CLOUD<br>'
        'PROTOCOL: CONSILIUM v1.0<br>'
        'VOTE: MAJORITY 2-OF-3<br>'
        'AUTH LEVEL: COMMANDER'
        '</div>',
        unsafe_allow_html=True,
    )

# ──────────────────────────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────────────────────────

st.markdown(
    '<div class="nerv-title" style="text-align:center;padding:24px 0 16px 0;'
    'border-bottom:1px solid #141414;margin-bottom:28px">'
    '<div style="color:#FF000088;font-size:0.58em;letter-spacing:6px;margin-bottom:6px">'
    'GEHIRN ARTIFICIAL EVOLUTION LABORATORY  ⬡  CLASSIFIED</div>'
    '<div style="color:#c8c8c8;font-size:2.2em;letter-spacing:10px;font-weight:normal">'
    'CONSILIUM MAGI</div>'
    '<div style="color:#2a2a2a;font-size:0.58em;letter-spacing:5px;margin-top:6px">'
    'MELCHIOR-1  ⬡  BALTHASAR-2  ⬡  CASPAR-3'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────
# TOPIC INPUT
# ──────────────────────────────────────────────────────────────────

client = get_client()

if not client:
    st.markdown(
        '<div style="color:#FF444488;font-size:0.72em;text-align:center;padding:14px;'
        'border:1px solid #FF444420;margin-bottom:20px;letter-spacing:2px">'
        '⚠  MAGI OFFLINE — ENTER GROQ API KEY IN SIDEBAR TO INITIATE'
        '</div>',
        unsafe_allow_html=True,
    )

topic_input = st.text_input(
    "QUERY",
    placeholder="Submit the question for MAGI deliberation...",
    disabled=not client,
    label_visibility="collapsed",
)

_, btn_col, _ = st.columns([2, 1, 2])
with btn_col:
    initiate = st.button(
        "INITIATE DELIBERATION",
        disabled=not client or not topic_input,
        use_container_width=True,
    )

if initiate and topic_input and client:
    st.session_state.debate_running = True
    st.session_state.current_topic = topic_input
    st.session_state.debate_results = None
    st.session_state.override = None

# ──────────────────────────────────────────────────────────────────
# DEBATE + VERDICT
# ──────────────────────────────────────────────────────────────────

if st.session_state.debate_running and client:
    st.markdown(
        f'<div style="color:#2e2e2e;font-size:0.62em;text-align:center;'
        f'margin:16px 0;letter-spacing:3px">'
        f'DELIBERATION IN PROGRESS — RE: {html_module.escape(st.session_state.current_topic)}'
        f'</div>',
        unsafe_allow_html=True,
    )
    results = run_debate(client, st.session_state.current_topic)
    st.session_state.debate_results = results
    st.session_state.debate_running = False
    show_verdict(results, st.session_state.override)

elif st.session_state.debate_results:
    st.markdown(
        f'<div style="color:#222;font-size:0.6em;text-align:center;'
        f'margin:16px 0;letter-spacing:3px">'
        f'RE: {html_module.escape(st.session_state.current_topic)}'
        f'</div>',
        unsafe_allow_html=True,
    )
    display_debate_static(st.session_state.debate_results)
    show_verdict(st.session_state.debate_results, st.session_state.override)

else:
    st.markdown(
        '<div style="color:#141414;font-size:0.75em;text-align:center;'
        'padding:80px 0;letter-spacing:3px;line-height:2.5">'
        'AWAITING COMMANDER INPUT<br>'
        '────────────────────<br>'
        'MAGI SYSTEM READY<br>'
        'ENTER QUERY TO BEGIN DELIBERATION'
        '</div>',
        unsafe_allow_html=True,
    )
