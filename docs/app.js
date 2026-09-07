/* Once Upon an Interrupt — frontend interruption engine.
 * Everything voice-critical lives client-side: the mic stays hot while the
 * narrator speaks, and interrupting = killing the local audio queue. */

// ---------- state ----------
const state = {
  sessionId: "s-" + Math.random().toString(36).slice(2, 10),
  mode: "story",
  voiceId: null,
  started: false,
  isSpeaking: false,
  thinking: false,
  audioQueue: [],        // [{sentence, audioB64|null}]
  currentAudio: null,
  currentUtterance: null, // speechSynthesis fallback
  currentSentence: "",
  spokenLog: [],          // sentences fully spoken this turn
  lastNarratorText: "",
  recognition: null,
  recognitionOn: false,
  mediaRecorder: null,
  recordedChunks: [],
};

// ---------- lite mode ----------
// On GitHub Pages there is no backend: a scripted narrator + browser voice
// power the same interruption engine. The full version (Llama + Fish.audio)
// runs via FastAPI — see the README.
const LITE = location.hostname.endsWith("github.io") || location.protocol === "file:";
const lite = { stance: "neutral", turn: 0 };

const LITE_ACKS = [
  "(chuckles) Oh, you have ideas? Go on then —",
  "(gasps) Cut off mid-sentence! Bold. Fine,",
  "Wait, switching things up already? I like the chaos —",
];
const LITE_STORY_OPENERS = [
  "Once upon a Tuesday, in a hostel room that smelled of instant noodles and ambition, our hero discovered the assignment was due at midnight. (gasps) And that was only the beginning. A dragon had been living in the mess hall, grading papers with fire. Our hero packed three pens and zero courage, and set off down the corridor.",
  "The library was silent, which was suspicious, because the library was never silent. Somewhere between the photocopier and the forbidden third shelf, something with scales was reading everyone's unfinished assignments aloud. (whispers) Our hero heard their own name. The deadline was in four hours.",
];
const LITE_STORY_CONTINUES = [
  "So it was decreed: STEER. The corridor lights flickered in agreement, nobody dared to question it, and the plot thickened like week-old dal. Our hero took a deep breath, because the next door had a nameplate that simply said: destiny, office hours 2 to 4.",
  "And just like that — STEER. (chuckles) The dragon blinked twice, the rulebook caught fire politely, and the story lurched in a direction no committee had approved. Our hero followed, mostly because running away was uphill.",
];
const LITE_DEBATE_ADV = [
  "Marriage, dear audience, is a lifetime group project where, surprisingly, someone may actually bring snacks. There is always a witness to your greatness and your kitchen disasters. Two incomes, one streaming password, infinite blame-sharing. (whispers) And someone to confirm the outfit is a crime before you leave the house.",
];
const LITE_DEBATE_DIS = [
  "(chuckles) Switching sides mid-vow? Dangerous, but accepted. Now, the disadvantages: marriage is a group project you cannot drop. The thermostat becomes a battlefield. Your snacks develop a mysterious second owner. Every argument you win, you somehow also lose. (sighs) Romance is just negotiation with candles.",
];

function litePick(arr) { return arr[lite.turn % arr.length]; }

function liteTurn(utterance, interruptedAt) {
  lite.turn++;
  const low = utterance.toLowerCase();
  let text;
  if (state.mode === "debate") {
    if (lite.stance === "neutral") {
      lite.stance = low.includes("disadvantage") ? "disadvantages" : "advantages";
      text = litePick(lite.stance === "disadvantages" ? LITE_DEBATE_DIS : LITE_DEBATE_ADV);
    } else {
      if (low.includes("disadvantage")) lite.stance = "disadvantages";
      else if (low.includes("advantage") || low.includes("benefit")) lite.stance = "advantages";
      else if (["switch", "flip", "opposite", "other side"].some((w) => low.includes(w)))
        lite.stance = lite.stance === "advantages" ? "disadvantages" : "advantages";
      text = litePick(lite.stance === "disadvantages" ? LITE_DEBATE_DIS : LITE_DEBATE_ADV);
    }
  } else if (interruptedAt || lite.turn > 1) {
    const steer = utterance || "keep going";
    text = (interruptedAt ? litePick(LITE_ACKS) + " " : "") +
      litePick(LITE_STORY_CONTINUES).replace("STEER", steer);
  } else {
    text = litePick(LITE_STORY_OPENERS);
  }
  const sentences = text.split(/(?<=[.!?])\s+/).filter(Boolean);
  return {
    ok: true, text, sentences,
    audio_chunks: sentences.map(() => null),
    provider: "browser-fallback", llm_provider: "lite-demo",
    stance: lite.stance, interruption_acknowledged: !!interruptedAt,
  };
}

// ---------- elements ----------
const $ = (id) => document.getElementById(id);
const el = {
  recordBtn: $("record-btn"), skipCloneBtn: $("skip-clone-btn"), cloneStatus: $("clone-status"),
  promptInput: $("prompt-input"), startBtn: $("start-btn"),
  statusBadge: $("status-badge"), micBadge: $("mic-badge"), voiceBadge: $("voice-badge"),
  transcript: $("transcript"), interruptPoint: $("interrupt-point"),
  interim: $("interim"), textInput: $("text-input"), sendBtn: $("send-btn"),
  interruptBtn: $("interrupt-btn"),
};

// ---------- status ----------
function setStatus(s) {
  el.statusBadge.textContent = s;
  el.statusBadge.className = "badge";
  if (s === "speaking") el.statusBadge.classList.add("speaking");
  if (s === "interrupted") el.statusBadge.classList.add("interrupted");
  if (s === "listening") el.statusBadge.classList.add("live");
}

function setVoiceBadge(provider) {
  el.voiceBadge.classList.remove("hidden");
  el.voiceBadge.textContent = provider === "fish.audio"
    ? (state.voiceId ? "Fish voice (cloned)" : "Fish voice")
    : "Browser voice";
}

function addTranscript(role, text) {
  const div = document.createElement("div");
  div.className = role;
  div.textContent = (role === "listener" ? "You: " : "") + text;
  el.transcript.appendChild(div);
  el.transcript.scrollTop = el.transcript.scrollHeight;
  return div;
}

// ---------- spoken-text tracking ----------
function spokenSoFar() {
  // best-effort prefix of what was actually voiced before the interrupt
  let text = state.spokenLog.join(" ");
  if (state.currentAudio && state.currentAudio.duration > 0) {
    const frac = Math.min(1, state.currentAudio.currentTime / state.currentAudio.duration);
    const words = state.currentSentence.split(/\s+/);
    text += " " + words.slice(0, Math.max(1, Math.round(words.length * frac))).join(" ");
  } else if (state.currentSentence) {
    text += " " + state.currentSentence; // speechSynthesis: sentence-level precision
  }
  return text.trim().split(/\s+/).slice(-14).join(" "); // last ~14 words
}

// ---------- audio playback ----------
function stopAllAudio() {
  state.audioQueue = [];
  if (state.currentAudio) { state.currentAudio.pause(); state.currentAudio = null; }
  if (window.speechSynthesis) speechSynthesis.cancel();
  state.currentUtterance = null;
  state.isSpeaking = false;
}

function playNext(narratorDiv) {
  const item = state.audioQueue.shift();
  if (!item) {
    if (state.currentSentence) state.spokenLog.push(state.currentSentence);
    state.currentSentence = "";
    state.isSpeaking = false;
    setStatus("listening");
    return;
  }
  if (state.currentSentence) state.spokenLog.push(state.currentSentence);
  state.currentSentence = item.sentence;
  state.isSpeaking = true;
  setStatus("speaking");
  highlightSpoken(narratorDiv);

  if (item.audioB64) {
    const audio = new Audio("data:audio/mp3;base64," + item.audioB64);
    state.currentAudio = audio;
    audio.onended = () => { state.currentAudio = null; playNext(narratorDiv); };
    audio.onerror = () => { state.currentAudio = null; speakFallback(item.sentence, narratorDiv); };
    audio.play().catch(() => speakFallback(item.sentence, narratorDiv));
  } else {
    speakFallback(item.sentence, narratorDiv);
  }
}

function speakFallback(sentence, narratorDiv) {
  if (!window.speechSynthesis) { playNext(narratorDiv); return; }
  const clean = sentence.replace(/\([a-z ]+\)/gi, ""); // strip (chuckles) markers
  const u = new SpeechSynthesisUtterance(clean);
  u.rate = 1.02; u.pitch = 1.05;
  u.onend = () => playNext(narratorDiv);
  u.onerror = () => playNext(narratorDiv);
  state.currentUtterance = u;
  speechSynthesis.speak(u);
}

function highlightSpoken(narratorDiv) {
  if (!narratorDiv) return;
  const done = state.spokenLog.join(" ");
  narratorDiv.innerHTML = "";
  const spoken = document.createElement("span");
  spoken.className = "spoken";
  spoken.textContent = (done ? done + " " : "") + state.currentSentence + " ";
  const rest = document.createElement("span");
  rest.textContent = state.audioQueue.map((i) => i.sentence).join(" ");
  narratorDiv.append(spoken, rest);
  el.transcript.scrollTop = el.transcript.scrollHeight;
}

// ---------- echo guard ----------
function normalize(s) { return s.toLowerCase().replace(/[^a-z0-9 ]/g, " ").replace(/\s+/g, " ").trim(); }

function isEcho(transcript) {
  const t = normalize(transcript);
  if (!t) return true;
  const recent = normalize(state.currentSentence + " " + state.lastNarratorText);
  if (recent.includes(t)) return true;
  const tWords = t.split(" ");
  if (tWords.length > 3) {
    const recentSet = new Set(recent.split(" "));
    const overlap = tWords.filter((w) => recentSet.has(w)).length / tWords.length;
    if (overlap > 0.75) return true;
  }
  return false;
}

const COMMAND_WORDS = ["switch", "flip", "opposite", "stop", "wait"];
function isMeaningful(transcript) {
  const t = normalize(transcript);
  if (COMMAND_WORDS.includes(t)) return true;
  return t.split(" ").length >= 2 && t.length >= 6;
}

// ---------- speech recognition ----------
function initRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    el.interim.textContent = "Mic recognition not supported here — use the text box below.";
    return null;
  }
  const rec = new SR();
  rec.continuous = true;
  rec.interimResults = true;
  rec.lang = "en-US";
  rec.onresult = (ev) => {
    let latest = "", isFinal = false;
    for (let i = ev.resultIndex; i < ev.results.length; i++) {
      latest += ev.results[i][0].transcript;
      if (ev.results[i].isFinal) isFinal = true;
    }
    latest = latest.trim();
    el.interim.textContent = latest || "…listening for your voice…";
    if (!latest || !isMeaningful(latest) || isEcho(latest)) return;
    if (state.isSpeaking) {
      interruptWith(latest);
    } else if (isFinal && state.started && !state.thinking) {
      sendTurn(latest, null);
    }
  };
  rec.onend = () => { if (state.recognitionOn) { try { rec.start(); } catch (_) {} } };
  rec.onerror = (e) => {
    if (e.error === "not-allowed") {
      el.interim.textContent = "Mic blocked — typed interruptions still work!";
      state.recognitionOn = false;
      el.micBadge.classList.add("hidden");
    }
  };
  return rec;
}

function startListening() {
  if (!state.recognition) state.recognition = initRecognition();
  if (!state.recognition || state.recognitionOn) return;
  try {
    state.recognition.start();
    state.recognitionOn = true;
    el.micBadge.classList.remove("hidden");
    el.micBadge.classList.add("live");
  } catch (_) {}
}

// ---------- core loop ----------
function interruptWith(utterance) {
  const cutAt = spokenSoFar();
  stopAllAudio();
  setStatus("interrupted");
  el.interruptPoint.classList.remove("hidden");
  el.interruptPoint.innerHTML = "✂️ Interrupted after: <span class='cutmark'>…" + cutAt + "</span>";
  addTranscript("listener", utterance + "  ✋");
  sendTurn(utterance, cutAt, true);
}

async function sendTurn(utterance, interruptedAt, wasInterrupt) {
  if (state.thinking) return;
  state.thinking = true;
  if (!wasInterrupt && utterance) addTranscript("listener", utterance);
  const wait = addTranscript("narrator", "The storyteller is clearing their throat…");
  setStatus("thinking");
  try {
    let data;
    if (LITE) {
      await new Promise((r) => setTimeout(r, 350)); // a beat of "thinking"
      data = liteTurn(utterance || "", interruptedAt || null);
    } else {
      const resp = await fetch("/turn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: state.sessionId,
          mode: state.mode,
          utterance: utterance || "",
          interrupted_at: interruptedAt || null,
          voice_id: state.voiceId,
        }),
      });
      data = await resp.json();
    }
    state.thinking = false;
    if (!data.ok) throw new Error("turn failed");
    state.lastNarratorText = data.text;
    state.spokenLog = [];
    state.currentSentence = "";
    setVoiceBadge(data.provider);
    wait.textContent = "";
    state.audioQueue = data.sentences.map((s, i) => ({ sentence: s, audioB64: data.audio_chunks[i] || null }));
    playNext(wait);
  } catch (err) {
    state.thinking = false;
    wait.textContent = "(the storyteller lost their voice — try again)";
    setStatus("idle");
  }
}

// ---------- voice clone ----------
async function toggleRecording() {
  if (state.mediaRecorder && state.mediaRecorder.state === "recording") {
    state.mediaRecorder.stop();
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.recordedChunks = [];
    const mr = new MediaRecorder(stream);
    state.mediaRecorder = mr;
    mr.ondataavailable = (e) => { if (e.data.size) state.recordedChunks.push(e.data); };
    mr.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      el.recordBtn.textContent = "🎙️ Record 20s voice sample";
      el.cloneStatus.textContent = "Uploading sample to the cloning cauldron…";
      const blob = new Blob(state.recordedChunks, { type: "audio/webm" });
      const form = new FormData();
      form.append("audio", blob, "sample.webm");
      try {
        const resp = await fetch("/clone", { method: "POST", body: form });
        const data = await resp.json();
        if (data.ok && data.voice_id) {
          state.voiceId = data.voice_id;
          el.cloneStatus.textContent = "✅ Voice cloned! The story will be told in YOUR voice.";
        } else {
          el.cloneStatus.textContent = "Cloning unavailable on this key — using demo voice instead.";
        }
      } catch (_) {
        el.cloneStatus.textContent = "Cloning failed — using demo voice instead.";
      }
    };
    mr.start();
    el.recordBtn.textContent = "⏹ Stop and clone voice";
    el.cloneStatus.textContent = "Recording… read anything aloud for ~20 seconds.";
    setTimeout(() => { if (mr.state === "recording") mr.stop(); }, 20000);
  } catch (_) {
    el.cloneStatus.textContent = "Mic unavailable — skip the clone and use the demo voice.";
  }
}

// ---------- wire up ----------
document.querySelectorAll("input[name=mode]").forEach((r) =>
  r.addEventListener("change", () => {
    state.mode = r.value;
    el.promptInput.placeholder = state.mode === "debate"
      ? "Tell us the advantages of marriage."
      : "Start a story about a dragon, a hostel room, and a missing assignment...";
  })
);

el.startBtn.addEventListener("click", () => {
  const prompt = el.promptInput.value.trim() || el.promptInput.placeholder;
  state.started = true;
  startListening();
  stopAllAudio();
  sendTurn(prompt, null);
});

el.interruptBtn.addEventListener("click", () => {
  if (state.isSpeaking) interruptWith("wait, let me steer this");
});

function sendTyped() {
  const text = el.textInput.value.trim();
  if (!text) return;
  el.textInput.value = "";
  if (state.isSpeaking) interruptWith(text);
  else sendTurn(text, null);
}
el.sendBtn.addEventListener("click", sendTyped);
el.textInput.addEventListener("keydown", (e) => { if (e.key === "Enter") sendTyped(); });

el.recordBtn.addEventListener("click", toggleRecording);
el.skipCloneBtn.addEventListener("click", () => {
  state.voiceId = null;
  el.cloneStatus.textContent = "Using the demo voice. You can clone later anytime.";
});

if (LITE) {
  el.voiceBadge.classList.remove("hidden");
  el.voiceBadge.textContent = "Lite demo · browser voice";
  el.cloneStatus.textContent =
    "Lite demo (GitHub Pages): scripted narrator + browser voice. " +
    "Run the repo locally for the Llama + Fish.audio full version.";
  el.recordBtn.disabled = true;
}

setStatus("idle");
