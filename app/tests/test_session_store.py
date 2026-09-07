from app.services.session_store import SessionStore


def test_create_session():
    store = SessionStore()
    sess = store.get_or_create("s1", mode="debate")
    assert sess.session_id == "s1"
    assert sess.mode == "debate"
    assert sess.stance == "neutral"
    assert store.get_or_create("s1") is sess


def test_append_turn():
    store = SessionStore()
    store.append_turn("s1", "listener", "start a story")
    store.append_turn("s1", "narrator", "Once upon a time.")
    sess = store.get("s1")
    assert len(sess.turns) == 2
    assert sess.last_text == "Once upon a time."


def test_reset_session():
    store = SessionStore()
    store.append_turn("s1", "narrator", "Hello.")
    store.reset("s1")
    assert store.get("s1") is None
    store.reset("never-existed")  # must not raise
