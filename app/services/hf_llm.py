"""Hugging Face Inference (OpenAI-compatible router) with a scripted local
fallback so the demo never dies on a cold or missing API."""
import random
from typing import List, Optional

import httpx

from app.config import settings

ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"

# Router-verified ids (2026-09): the router serves Llama without the "Meta-"
# prefix; Mistral-7B/zephyr are not chat-servable on this key, so they are
# not listed — the scripted local_fallback below is the real safety net.
FALLBACK_MODELS = [
    "meta-llama/Llama-3.1-8B-Instruct",
    "meta-llama/Llama-3.3-70B-Instruct",
]


def _candidate_models() -> List[str]:
    models = [settings.hf_model] + FALLBACK_MODELS
    seen, out = set(), []
    for m in models:
        if m and m not in seen:
            seen.add(m)
            out.append(m)
    return out


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


async def _try_chat(client, url, headers, model, messages) -> Optional[str]:
    for _ in range(2):
        try:
            resp = await client.post(
                url,
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": 260,
                    "temperature": 0.9,
                },
            )
            if resp.status_code == 200:
                text = resp.json()["choices"][0]["message"]["content"].strip()
                if text:
                    return text
            return None  # non-200: caller moves to next model/provider
        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            continue
    return None


async def generate(messages: List[dict]) -> Optional[str]:
    """Return narrator text from Groq (fastest) or HF, else None -> local fallback."""
    if not settings.has_hf and not settings.has_groq:
        return None
    # transport-level retries: the HF router CDN drops TLS connects sometimes
    transport = httpx.AsyncHTTPTransport(retries=3)
    async with httpx.AsyncClient(timeout=25, transport=transport) as client:
        if settings.has_groq:
            text = await _try_chat(
                client,
                GROQ_URL,
                {"Authorization": f"Bearer {settings.groq_api_key}"},
                settings.groq_model,
                messages,
            )
            if text:
                return text
        if settings.has_hf:
            headers = {"Authorization": f"Bearer {settings.huggingface_api_key}"}
            for model in _candidate_models():
                text = await _try_chat(client, ROUTER_URL, headers, model, messages)
                if text:
                    return text
    return None


# ---------------------------------------------------------------------------
# Scripted local fallback — keeps the interruption demo alive with zero APIs.
# ---------------------------------------------------------------------------

_STORY_OPENERS = [
    "Once upon a Tuesday, in a hostel room that smelled of instant noodles and ambition, "
    "our hero discovered the assignment was due at midnight. (gasps) And that was only "
    "the beginning. A dragon, you see, had been living in the mess hall, grading papers "
    "with fire. The hero packed three pens and zero courage, and set off down the corridor.",
]

_STORY_INTERRUPTED = [
    "(chuckles) Oh, you have ideas? Go on then — {steer}. Very well! The tale bends to "
    "your will: {steer}, and nobody in the story was brave enough to question it. "
    "The plot thickened like week-old dal, and our hero simply had to keep walking.",
]

_DEBATE_ADVANTAGES = [
    "Marriage, dear audience, is a lifetime group project where, surprisingly, someone "
    "may actually bring snacks. There is always a witness to your greatness and your "
    "kitchen disasters. Two incomes, one Netflix account, infinite blame-sharing. "
    "(whispers) And someone to check if that outfit is a crime.",
]

_DEBATE_DISADVANTAGES = [
    "(chuckles) Switching sides mid-vow? Dangerous, but accepted. Now, the disadvantages: "
    "marriage is a group project where you cannot drop the course. The thermostat becomes "
    "a battlefield. Your snacks develop a mysterious second owner. And every argument you "
    "win, you somehow also lose. (sighs) Romance is just negotiation with candles.",
]


def local_fallback(
    mode: str,
    stance: str,
    utterance: str,
    interrupted_at: Optional[str],
    pivot: bool,
) -> str:
    steer = utterance.strip() or "keep going"
    if mode == "debate":
        if stance == "disadvantages":
            base = random.choice(_DEBATE_DISADVANTAGES)
        else:
            base = random.choice(_DEBATE_ADVANTAGES)
        if pivot:
            return base
        if interrupted_at:
            return f"(chuckles) You cut me off mid-flourish — I respect it. {base}"
        return base
    # story mode
    if interrupted_at:
        return random.choice(_STORY_INTERRUPTED).format(steer=steer)
    return random.choice(_STORY_OPENERS)
