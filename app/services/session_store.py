"""In-memory session store. One process, no database — hackathon scale."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Session:
    session_id: str
    mode: str = "story"
    stance: str = "neutral"  # debate mode: advantages | disadvantages | neutral
    turns: List[dict] = field(default_factory=list)  # {"role": ..., "text": ...}
    last_text: str = ""
    interrupted_at: Optional[str] = None
    voice_id: Optional[str] = None


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, Session] = {}

    def get_or_create(self, session_id: str, mode: str = "story") -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id=session_id, mode=mode)
        return self._sessions[session_id]

    def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def append_turn(self, session_id: str, role: str, text: str) -> None:
        sess = self.get_or_create(session_id)
        sess.turns.append({"role": role, "text": text})
        if role == "narrator":
            sess.last_text = text

    def reset(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


store = SessionStore()
