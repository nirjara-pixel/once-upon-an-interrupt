"""Fish.audio integration: instant voice cloning + TTS.

Kept deliberately small and isolated so endpoint details can be corrected
fast if the free tier differs. Every function degrades to None — callers
then fall back to browser speechSynthesis.
"""
from typing import Optional

import httpx

from app.config import settings

BASE_URL = "https://api.fish.audio"


def _headers(extra: Optional[dict] = None) -> dict:
    h = {"Authorization": f"Bearer {settings.fish_audio_api_key}"}
    if extra:
        h.update(extra)
    return h


async def synthesize(text: str, voice_id: Optional[str] = None) -> Optional[bytes]:
    """Return mp3 bytes for one sentence, or None to trigger the fallback."""
    if not settings.has_fish or not text.strip():
        return None
    payload = {"text": text, "format": "mp3", "latency": "balanced"}
    if voice_id:
        payload["reference_id"] = voice_id
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{BASE_URL}/v1/tts",
                json=payload,
                headers=_headers({"model": settings.fish_tts_model}),
            )
            if resp.status_code == 200 and resp.content:
                return resp.content
    except httpx.HTTPError:
        pass
    return None


async def clone_voice(
    audio_bytes: bytes, filename: str, content_type: str
) -> Optional[str]:
    """Create a private voice model from a short sample; returns its id."""
    if not settings.has_fish or not audio_bytes:
        return None
    data = {
        "visibility": "private",
        "type": "tts",
        "title": "Once Upon an Interrupt narrator",
        "train_mode": "fast",
    }
    files = {"voices": (filename, audio_bytes, content_type)}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{BASE_URL}/model", data=data, files=files, headers=_headers()
            )
            if resp.status_code in (200, 201):
                return resp.json().get("_id")
    except (httpx.HTTPError, ValueError):
        pass
    return None
