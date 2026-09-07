"""Once Upon an Interrupt — a voice you can interrupt, even when it is yours."""
import asyncio
import base64
import re
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.models import ResetRequest, TurnRequest
from app.services import fish_audio, hf_llm
from app.services.fallback_tts import choose_provider
from app.services.session_store import Session, store

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"
MAX_TTS_SENTENCES = 8  # cap Fish calls per turn to protect free credits

app = FastAPI(title="Once Upon an Interrupt")
app.mount("/static", StaticFiles(directory=str(PUBLIC_DIR)), name="static")

SYSTEM_PROMPT = """You are "Once Upon an Interrupt", a playful narrator designed to be interrupted. You speak in vivid, short, performable sentences. The user may interrupt you mid-sentence. When interrupted, you must acknowledge the interruption naturally, then continue from that exact point while following the user's new direction.

Rules:
- Keep responses under 120 words unless the user asks for more.
- Use expressive stage directions sparingly, such as (chuckles), (gasps), (whispers), but do not overdo it.
- If an interruption point is provided, explicitly react to the interruption.
- Never restart from the beginning unless the user asks.
- In story mode, continue the story and weave in the user steer.
- In debate mode, behave like a funny debate host. Track the current stance. If the user says switch/flip/opposite/disadvantages/advantages, immediately change stance and announce the pivot humorously.
- Make the interruption feel like a feature, not an error."""

GENERIC_SWITCH_WORDS = ("switch", "flip", "opposite", "other side")


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _flip(stance: str) -> str:
    return "advantages" if stance == "disadvantages" else "disadvantages"


def update_debate_stance(sess: Session, utterance: str) -> bool:
    """Update the session stance from the utterance. Returns True on a pivot."""
    low = utterance.lower()
    first_turn = not sess.turns
    if first_turn or sess.stance == "neutral":
        # Opening prompt sets the stance; check 'disadvantage' first since
        # the word contains 'advantage'.
        if "disadvantage" in low or "cons" in low:
            sess.stance = "disadvantages"
        else:
            sess.stance = "advantages"
        return False
    old = sess.stance
    if "disadvantage" in low:
        sess.stance = "disadvantages"
    elif "advantage" in low or "benefit" in low or "pros" in low:
        sess.stance = "advantages"
    elif any(w in low for w in GENERIC_SWITCH_WORDS):
        sess.stance = _flip(sess.stance)
    return sess.stance != old


def build_messages(
    sess: Session, utterance: str, interrupted_at: Optional[str], pivot: bool
) -> List[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in sess.turns[-8:]:
        role = "assistant" if turn["role"] == "narrator" else "user"
        messages.append({"role": role, "content": turn["text"]})
    parts = []
    if sess.mode == "debate":
        parts.append(f"[Debate mode. Current stance to argue: {sess.stance}.]")
        if pivot:
            parts.append(
                "[The listener just demanded you SWITCH SIDES. Acknowledge the pivot "
                "with humor and argue the new stance from here on.]"
            )
    if interrupted_at:
        parts.append(
            f'[The narrator was interrupted after: "...{interrupted_at}". '
            "React to being cut off, then continue from that exact point.]"
        )
    parts.append(f"The listener says: {utterance}" if utterance else "Begin.")
    messages.append({"role": "user", "content": "\n".join(parts)})
    return messages


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(PUBLIC_DIR / "index.html")


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "service": "once-upon-an-interrupt"}


@app.post("/clone")
async def clone(audio: UploadFile = File(...)) -> dict:
    audio_bytes = await audio.read()
    voice_id = await fish_audio.clone_voice(
        audio_bytes, audio.filename or "sample.webm", audio.content_type or "audio/webm"
    )
    if voice_id:
        return {"ok": True, "voice_id": voice_id, "provider": "fish.audio"}
    return {
        "ok": False,
        "voice_id": None,
        "provider": "fallback",
        "message": "Voice cloning unavailable; using fallback voice.",
    }


@app.post("/turn")
async def turn(req: TurnRequest) -> dict:
    sess = store.get_or_create(req.session_id, req.mode)
    sess.mode = req.mode
    if req.voice_id:
        sess.voice_id = req.voice_id
    utterance = req.utterance.strip()
    interrupted = bool(req.interrupted_at)
    sess.interrupted_at = req.interrupted_at

    pivot = False
    if req.mode == "debate":
        pivot = update_debate_stance(sess, utterance)

    messages = build_messages(sess, utterance, req.interrupted_at, pivot)
    text = await hf_llm.generate(messages)
    llm_provider = "huggingface"
    if not text:
        text = hf_llm.local_fallback(
            sess.mode, sess.stance, utterance, req.interrupted_at, pivot
        )
        llm_provider = "local-fallback"

    sentences = split_sentences(text)
    audio_chunks: List[Optional[str]] = [None] * len(sentences)
    if not req.force_fallback_tts and settings.has_fish:
        raw = await asyncio.gather(
            *[
                fish_audio.synthesize(s, sess.voice_id)
                for s in sentences[:MAX_TTS_SENTENCES]
            ]
        )
        for i, chunk in enumerate(raw):
            if chunk:
                audio_chunks[i] = base64.b64encode(chunk).decode()

    if utterance:
        store.append_turn(req.session_id, "listener", utterance)
    store.append_turn(req.session_id, "narrator", text)

    return {
        "ok": True,
        "session_id": req.session_id,
        "text": text,
        "sentences": sentences,
        "audio_chunks": audio_chunks,
        "provider": choose_provider(audio_chunks),
        "llm_provider": llm_provider,
        "stance": sess.stance,
        "interruption_acknowledged": interrupted,
    }


@app.post("/reset")
async def reset(req: ResetRequest) -> dict:
    store.reset(req.session_id)
    return {"ok": True}
