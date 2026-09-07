"""Smoke test for the Hugging Face key: tries each candidate chat model.

Usage:  python scripts/smoke_test_hf.py
Reads HUGGINGFACE_API_KEY from the environment / .env.
"""
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

KEY = os.getenv("HUGGINGFACE_API_KEY", "")
MODELS = [
    os.getenv("HF_MODEL", "meta-llama/Llama-3.1-8B-Instruct"),
    "meta-llama/Llama-3.1-8B-Instruct",
    "meta-llama/Llama-3.3-70B-Instruct",
]

if not KEY or KEY == "replace_me":
    sys.exit("HUGGINGFACE_API_KEY missing — set it in .env")

ok = []
for model in dict.fromkeys(MODELS):
    try:
        resp = httpx.post(
            "https://router.huggingface.co/v1/chat/completions",
            headers={"Authorization": f"Bearer {KEY}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Say 'ready' in 3 words."}],
                "max_tokens": 20,
            },
            timeout=45,
        )
        if resp.status_code == 200:
            text = resp.json()["choices"][0]["message"]["content"].strip()
            print(f"model={model!r}: OK -> {text[:60]!r}")
            ok.append(model)
        else:
            print(f"model={model!r}: HTTP {resp.status_code} {resp.text[:120]}")
    except httpx.HTTPError as e:
        print(f"model={model!r}: error {e}")

if ok:
    print(f"\nWORKING MODELS: {ok} — set HF_MODEL={ok[0]} in .env")
else:
    print("\nNo model worked. The app will use the scripted local fallback.")
    sys.exit(1)
