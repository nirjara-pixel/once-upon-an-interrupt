from typing import Literal, Optional
from pydantic import BaseModel


class TurnRequest(BaseModel):
    session_id: str
    mode: Literal["story", "debate"] = "story"
    utterance: str = ""
    interrupted_at: Optional[str] = None
    voice_id: Optional[str] = None
    force_fallback_tts: bool = False


class ResetRequest(BaseModel):
    session_id: str
