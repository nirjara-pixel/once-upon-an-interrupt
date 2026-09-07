"""Server-side marker for the browser speechSynthesis fallback.

The actual fallback voice runs in the browser (speechSynthesis). The server
just signals it by returning provider="browser-fallback" and no audio chunks;
this module centralises that contract so /turn stays readable.
"""
from typing import List, Optional

BROWSER_FALLBACK = "browser-fallback"
FISH_PROVIDER = "fish.audio"


def choose_provider(audio_chunks: List[Optional[str]]) -> str:
    """Fish counts as active only if at least one sentence actually got audio."""
    return FISH_PROVIDER if any(audio_chunks) else BROWSER_FALLBACK
