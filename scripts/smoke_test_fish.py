"""Smoke test for the Fish.audio key: finds which TTS model header works.

Usage:  python scripts/smoke_test_fish.py
Reads FISH_AUDIO_API_KEY from the environment / .env. Writes no audio to git.
"""
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

KEY = os.getenv("FISH_AUDIO_API_KEY", "")
CANDIDATES = ["s2.1-pro-free", "s1", "speech-1.5", "speech-1.6", "speech-2.5-pro"]

if not KEY or KEY == "replace_me":
    sys.exit("FISH_AUDIO_API_KEY missing — set it in .env")

ok = []
for model in CANDIDATES:
    try:
        resp = httpx.post(
            "https://api.fish.audio/v1/tts",
            json={"text": "Once upon an interrupt. (chuckles)", "format": "mp3"},
            headers={"Authorization": f"Bearer {KEY}", "model": model},
            timeout=30,
        )
        status = resp.status_code
        size = len(resp.content) if status == 200 else 0
        print(f"model={model!r}: HTTP {status}, {size} bytes")
        if status == 200 and size > 1000:
            ok.append(model)
    except httpx.HTTPError as e:
        print(f"model={model!r}: error {e}")

if ok:
    print(f"\nWORKING MODELS: {ok} — set FISH_TTS_MODEL={ok[0]} in .env")
else:
    print("\nNo model worked. Check the key, credits, or endpoint docs.")
    sys.exit(1)
