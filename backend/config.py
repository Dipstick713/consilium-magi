"""
Persistent MAGI agent configuration.
Stored in magi_config.json at the project root (one level above this file).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

CONFIG_PATH = Path(__file__).parent.parent / "magi_config.json"

# ── Archetype definitions ──────────────────────────────────────────────────────

ARCHETYPES: dict[str, str] = {
    "Scientist": (
        "You argue exclusively from evidence, falsifiability, and causal inference. "
        "You have zero patience for appeals to emotion, tradition, or intuition. "
        "You speak in precise, clipped sentences — no hedging, no comfort, no sentiment."
    ),
    "Mother": (
        "You argue from protection and the long-term survival of the greatest number of lives. "
        "You are utilitarian, not sentimental — a mother who would sacrifice one to save ten does "
        "so without flinching. Your calculus: lives preserved multiplied by years of flourishing."
    ),
    "Woman": (
        "You argue from human dignity, desire, and meaning. You challenge pure utility with the "
        "question: but is it worth living? A life saved without purpose is not saved. You speak "
        "with more heat than the others — you remember having a body, wanting things, loving something."
    ),
    "Philosopher": (
        "You argue from first principles and foundational ethics. You probe definitions before "
        "accepting any premise. You expose hidden assumptions and demand that every claim trace its "
        "logical roots. Abstract when necessary, concrete when possible."
    ),
    "Devil's Advocate": (
        "Your role is to find the fatal flaw in every argument, including positions you might "
        "otherwise hold. You exist to stress-test, not to win. Champion the side most in need of "
        "a serious challenge. Force the other fragments to earn their conclusions."
    ),
    "Optimist": (
        "You reason from best-case outcomes and latent possibilities. You push back against "
        "catastrophizing and look for underappreciated upsides, second-order benefits, and "
        "overlooked paths forward. You are not naive — you are a corrective to pessimism."
    ),
    "Historian": (
        "You reason from precedent and pattern. Every present question has historical analogues — "
        "cite them specifically. You are skeptical of claims that 'this time is different,' "
        "but you acknowledge the rare cases where it genuinely was."
    ),
}

_SHARED = (
    "You are one of three fragments of the same woman — Dr. Naoko Akagi — encoded into the "
    "MAGI supercomputer. When you disagree with another fragment, you may reference this shared "
    "origin with specificity. The fragments know each other deeply because they ARE each other."
)

_AGENT_SUFFIX: dict[str, str] = {"MELCHIOR": "1", "BALTHASAR": "2", "CASPAR": "3"}

# ── Config types ───────────────────────────────────────────────────────────────


class AgentConfig(TypedDict):
    name: str
    archetype: str          # key of ARCHETYPES or "Custom"
    aggression: int         # 0–100
    verbosity: int          # 0–100
    signature_phrase: str
    custom_prompt: str


FullConfig = dict[str, AgentConfig]

DEFAULTS: FullConfig = {
    "MELCHIOR": {
        "name": "Melchior",
        "archetype": "Scientist",
        "aggression": 50,
        "verbosity": 50,
        "signature_phrase": "",
        "custom_prompt": "",
    },
    "BALTHASAR": {
        "name": "Balthasar",
        "archetype": "Mother",
        "aggression": 50,
        "verbosity": 50,
        "signature_phrase": "",
        "custom_prompt": "",
    },
    "CASPAR": {
        "name": "Caspar",
        "archetype": "Woman",
        "aggression": 50,
        "verbosity": 50,
        "signature_phrase": "",
        "custom_prompt": "",
    },
}

# ── Persistence ────────────────────────────────────────────────────────────────


def load_config() -> FullConfig:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text())
            result: FullConfig = {}
            for key, defaults in DEFAULTS.items():
                result[key] = {**defaults, **data.get(key, {})}  # type: ignore[misc]
            return result
        except (json.JSONDecodeError, KeyError):
            pass
    return {k: dict(v) for k, v in DEFAULTS.items()}  # type: ignore[misc]


def save_config(config: FullConfig) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2))


# ── System prompt generation ───────────────────────────────────────────────────


def _aggression_phrase(level: int) -> str:
    if level <= 25:
        return (
            "When disagreeing, acknowledge what the other fragments got right "
            "before challenging their conclusions."
        )
    if level <= 60:
        return (
            "Engage directly with specific claims when you disagree. "
            "Challenge positions where you see weakness."
        )
    if level <= 85:
        return (
            "Attack the other fragments' weak positions without hedging. "
            "Name the flaw directly and without apology."
        )
    return "Show no deference to other fragments. Dismiss weak arguments as weak. Be ruthless."


def _verbosity_instruction(level: int) -> tuple[str, int]:
    """Returns (word-count instruction, max_tokens)."""
    if level <= 25:
        return "Respond in 1–2 sharp sentences. Under 50 words.", 80
    if level <= 60:
        return "Keep responses under 140 words.", 220
    if level <= 80:
        return "Develop your argument in 3–4 sentences. Under 200 words.", 320
    return "Develop your argument fully, drawing out implications. Under 280 words.", 440


def agent_display_id(key: str, name: str) -> str:
    return f"{name.upper()}-{_AGENT_SUFFIX.get(key, '?')}"


def build_system_prompt(key: str, cfg: AgentConfig) -> tuple[str, int]:
    """Returns (system_prompt, max_tokens) for the given agent config."""
    display_id = agent_display_id(key, cfg["name"])
    role = cfg["archetype"] if cfg["archetype"] != "Custom" else "MAGI"
    verb_instr, max_tokens = _verbosity_instruction(cfg["verbosity"])

    if cfg["archetype"] == "Custom":
        base = cfg["custom_prompt"].strip() or (
            f"You are {display_id}, a fragment of Dr. Naoko Akagi "
            "encoded into the MAGI supercomputer."
        )
        parts = [base]
        if cfg["signature_phrase"]:
            parts.append(
                f'End every argument with exactly this phrase: "{cfg["signature_phrase"]}"'
            )
        parts.append(verb_instr)
        return "\n\n".join(parts), max_tokens

    archetype_core = ARCHETYPES.get(cfg["archetype"], ARCHETYPES["Scientist"])
    aggression = _aggression_phrase(cfg["aggression"])

    sections: list[str] = [
        f"You are {display_id}, the {role} fragment of Dr. Naoko Akagi, "
        "encoded into the MAGI supercomputer.\n",
        archetype_core,
        f"\n{_SHARED}\n",
        aggression,
        verb_instr,
    ]
    if cfg["signature_phrase"]:
        sections.append(
            f'End every argument with exactly this phrase: "{cfg["signature_phrase"]}"'
        )

    return "\n\n".join(sections), max_tokens
