# Demo Video Script — Once Upon an Interrupt (90 seconds)

Problem 5 · "A Voice You Can Interrupt" · ITGeeks Vibe Coding Round

## Pre-flight checklist (do BEFORE recording)

- [ ] **Earphones in** — the mic must never hear the narrator's speaker output (keeps the echo guard trivial and barge-in crisp).
- [ ] **Chrome** (desktop), latest version — best Web Speech API support.
- [ ] **Mic permission already granted** for `localhost:8000` (click Start once beforehand so no permission popup appears on camera).
- [ ] **APIs warm**: run `python scripts/smoke_test_hf.py` and `python scripts/smoke_test_fish.py`, then do one throwaway `/turn` in the app so the first on-camera response lands in ~1–2s.
- [ ] Server running: `uvicorn app.main:app --reload`, `/health` returns ok.
- [ ] Tests green locally: `python -m pytest` (you'll show this at the end).
- [ ] Close notification apps; quiet room; screen recorder capturing **system audio + mic**.

## Camera / screen tips

- Record the screen at full resolution; keep the browser at ~110% zoom so badges and the ✂️ line are readable.
- Keep your voice close to the mic and speak interruptions **confidently over the narrator** — hesitant half-words may be filtered as noise.
- Let the ✂️ interruption line and the "interrupted" badge sit on screen ~2s each time — they are the proof shots.
- If a take stumbles, click a mode radio + Start again for a fresh turn; session resets via `/reset` if needed.

## Shot-by-shot

### 0–10s — The problem and the claim
- **Screen:** README.md open at the top: title, pitch, and the "Problem 5 · A Voice You Can Interrupt" section, then a beat on the self-defined acceptance criteria list.
- **Voiceover:** "The challenge gave us only a title: a voice you can interrupt. So we defined the acceptance criteria ourselves — and now we prove every one of them."

### 10–25s — Open the app, clone (or skip) the voice
- **Screen:** Switch to `http://localhost:8000`. Show card 1, click **🎙️ Record 20s voice sample**, read a line aloud, stop → status shows the clone result. (If cloning is unavailable on the key, click **Skip clone, use demo voice** and say so honestly — the fallback IS a feature.)
- **Voiceover:** "First, the narrator borrows my voice — twenty seconds recorded right in the browser, cloned through Fish.audio. If cloning isn't available, it gracefully falls back."

### 25–40s — Story Mode: the narrator speaks
- **Screen:** Card 2: Story Mode selected, prompt "Start a story about a dragon, a hostel room, and a missing assignment", click **▶ Start talking**. Show "The storyteller is clearing their throat…" flip into live speech; point at the **speaking** badge and the **Mic active** badge glowing at the same time.
- **Voiceover:** "Story mode. Note the two badges: the narrator is speaking AND the mic is still live. That's the whole trick."

### 40–55s — Interrupt by voice (the money shot)
- **Screen:** While the narrator is mid-sentence, say clearly: **"Make the dragon my strict professor."** Playback dies mid-word. The UI shows **✂️ Interrupted after: "…"** with the exact last words voiced. The narrator chuckles, acknowledges being cut off, and continues from that point with the professor-dragon steer.
- **Voiceover:** (let the app's own audio carry this beat) then: "Stopped mid-word. It marked exactly where I cut it off, laughed about it, and picked the story up from that precise point — with my change."

### 55–75s — Switch Debate Mode
- **Screen:** Select **🎭 Switch Debate Mode**, prompt "Tell us the advantages of marriage", Start. Narrator argues advantages; a few seconds in, say **"switch"**. Audio dies, ✂️ point shows, narrator flips to funny disadvantages, announcing the pivot from the interrupted point.
- **Voiceover:** "Debate mode. It's arguing FOR marriage… until I say one word — switch — and it flips sides mid-argument, from exactly where I stopped it."

### 75–90s — Proof and closing
- **Screen:** GitHub repo page, then a terminal running `python -m pytest` → green, and/or the green CI badge/run.
- **Voiceover:** "Backend, fallbacks, and the interruption logic are all tested and green in CI. Once Upon an Interrupt: a voice you can interrupt — even when it is yours."

## Timing safety

If a segment runs long, trim shot 2 (clone) to a fast skip — shots 4 and 5 (voice barge-in + switch) are the non-negotiable proof of the acceptance criteria.
