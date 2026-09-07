import pytest
from fastapi.testclient import TestClient

from app import main
from app.services.session_store import store


@pytest.fixture(autouse=True)
def mock_external(monkeypatch):
    """Mock HF and Fish so tests never touch the network."""

    async def fake_generate(messages):
        return "The dragon opened its eyes. (gasps) It graded in red fire."

    async def fake_synthesize(text, voice_id=None):
        return None  # exercise the browser-fallback path

    monkeypatch.setattr(main.hf_llm, "generate", fake_generate)
    monkeypatch.setattr(main.fish_audio, "synthesize", fake_synthesize)
    yield
    store.reset("t1")
    store.reset("t2")


client = TestClient(main.app)


def test_health():
    resp = client.get("/health")
    assert resp.json() == {"ok": True, "service": "once-upon-an-interrupt"}


def test_turn_returns_ok():
    resp = client.post(
        "/turn",
        json={"session_id": "t1", "mode": "story", "utterance": "Start a dragon story"},
    )
    body = resp.json()
    assert body["ok"] is True
    assert body["text"]
    assert body["sentences"]
    assert len(body["audio_chunks"]) == len(body["sentences"])
    assert body["provider"] == "browser-fallback"
    assert body["interruption_acknowledged"] is False


def test_turn_acknowledges_interruption():
    resp = client.post(
        "/turn",
        json={
            "session_id": "t1",
            "mode": "story",
            "utterance": "make the dragon my strict professor",
            "interrupted_at": "and the dragon opened its",
        },
    )
    assert resp.json()["interruption_acknowledged"] is True


def test_debate_switch_flips_stance():
    resp = client.post(
        "/turn",
        json={
            "session_id": "t2",
            "mode": "debate",
            "utterance": "Tell us advantages of marriage.",
        },
    )
    assert resp.json()["stance"] == "advantages"

    resp = client.post(
        "/turn",
        json={
            "session_id": "t2",
            "mode": "debate",
            "utterance": "switch",
            "interrupted_at": "someone may actually bring snacks",
        },
    )
    body = resp.json()
    assert body["stance"] == "disadvantages"
    assert body["interruption_acknowledged"] is True
