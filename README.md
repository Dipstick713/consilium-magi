# CONSILIUM MAGI

> *The three MAGI are not computers. They are fragments of a woman.*

A Streamlit application inspired by the MAGI supercomputer system from *Neon Genesis Evangelion*. Three AI agents — each a different fragment of Dr. Naoko Akagi's psyche — debate any question from their distinct psychological lenses, then cast a formal 2-of-3 majority vote. You play Commander and may override at any time.

---

## The Fragments

| Unit | Fragment | Lens | Color |
|------|----------|------|-------|
| **MELCHIOR-1** | The Scientist | Evidence, falsifiability, causal inference — cold, precise, no sentiment | Amber |
| **BALTHASAR-2** | The Mother | Utilitarian protection; survival of the greatest number over the longest timeframe | Green |
| **CASPAR-3** | The Woman | Human dignity, desire, meaning — *but is it worth living?* | Purple |

Each agent knows the others are fragments of herself. They reference this shared origin when they disagree, which creates dramatic tension.

---

## Protocol

1. Submit a question to the MAGI
2. **Round 1** — each fragment states its opening position
3. **Round 2** — each fragment responds to the others, attacking or advancing
4. **Vote** — each fragment renders a formal `APPROVE` or `REJECT` with a one-sentence reason
5. **Verdict** — 2-of-3 majority rules
6. **Commander Override** — you may override the verdict in either direction

---

## Setup

```bash
# 1. Clone / enter the repo
cd consilium-magi

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your Groq API key (get one free at console.groq.com)
export GROQ_API_KEY="gsk_..."

# 4. Run
streamlit run app.py
```

Alternatively, enter your Groq API key directly in the sidebar — no environment variable needed.

---

## Stack

- **Frontend:** Streamlit with custom NERV terminal CSS
- **LLM:** `llama-3.3-70b-versatile` via Groq API (streaming)
- **Font:** Share Tech Mono (loaded from Google Fonts)

---

## Aesthetic

Dark background · monospace throughout · amber / green / purple agent accents · no Streamlit chrome · subtle scanline flicker on the header title.
