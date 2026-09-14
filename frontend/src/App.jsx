import { useEffect, useRef, useState } from "react";
import { announcePayment, getMerchant, nextPayment, resetDemo } from "./api.js";
import { BEATS } from "./pitch.js";
import Counter from "./screens/Counter.jsx";
import Scoreboard from "./screens/Scoreboard.jsx";
import Pruning from "./screens/Pruning.jsx";
import Privacy from "./screens/Privacy.jsx";
import Close from "./screens/Close.jsx";

const SCREENS = ["counter", "scoreboard", "pruning", "privacy", "close"];

function fmt(ms) {
  const total = Math.min(180, Math.max(0, Math.floor(ms / 1000)));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export default function App() {
  const [screen, setScreen] = useState(() => {
    const h = window.location.hash.replace("#", "");
    return SCREENS.includes(h) ? h : "counter";
  });
  const [merchant, setMerchant] = useState(null);
  const [event, setEvent] = useState(null);
  const [busy, setBusy] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [pitching, setPitching] = useState(false);
  const [beat, setBeat] = useState(null);
  const [note, setNote] = useState("");
  const [notesOn, setNotesOn] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const busyRef = useRef(false);
  const playRef = useRef(false);
  const pitchRef = useRef(null);
  const fireRef = useRef(async () => {});

  useEffect(() => {
    busyRef.current = busy;
  }, [busy]);

  useEffect(() => {
    getMerchant().then(setMerchant).catch(() => {});
    window.speechSynthesis?.getVoices();
    function onHash() {
      const h = window.location.hash.replace("#", "");
      if (SCREENS.includes(h)) setScreen(h);
    }
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    const es = new EventSource("/stream");
    es.onmessage = (m) => {
      if (!m.data) return;
      try {
        const data = JSON.parse(m.data);
        if (data.payment_id) setEvent(data);
      } catch {
        /* ping / hello */
      }
    };
    return () => es.close();
  }, []);

  async function fireNext() {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    try {
      const data = await nextPayment();
      setEvent(data);
      announcePayment(data);
      if (data.demo && data.demo.index >= data.demo.total) {
        playRef.current = false;
        setPlaying(false);
      }
    } finally {
      setTimeout(() => {
        busyRef.current = false;
        setBusy(false);
      }, 400);
    }
  }

  fireRef.current = fireNext;

  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => {
      if (!playRef.current) return;
      fireRef.current();
    }, 2800);
    return () => clearInterval(id);
  }, [playing]);

  function go(name) {
    setScreen(name);
    window.location.hash = name;
  }

  function stopPitch() {
    if (pitchRef.current?.timers) pitchRef.current.timers.forEach(clearTimeout);
    pitchRef.current = null;
    setPitching(false);
    setElapsed(0);
  }

  function startPitch() {
    stopPitch();
    playRef.current = false;
    setPlaying(false);
    resetDemo().then(() => {
      setEvent(null);
      setBeat("open");
      setNote(BEATS[0].note);
      go("counter");
      const t0 = Date.now();
      const timers = BEATS.map((b) =>
        setTimeout(() => {
          if (b.end) {
            stopPitch();
            return;
          }
          if (b.screen) go(b.screen);
          if (b.beat !== undefined) setBeat(b.beat);
          if (b.note) setNote(b.note);
          if (b.fire) fireRef.current();
        }, b.at)
      );
      pitchRef.current = { t0, timers };
      setPitching(true);
    });
  }

  useEffect(() => {
    if (!pitching || !pitchRef.current) return;
    const id = setInterval(() => {
      setElapsed(Date.now() - pitchRef.current.t0);
    }, 250);
    return () => clearInterval(id);
  }, [pitching]);

  useEffect(() => {
    function onKey(e) {
      if (e.target?.matches?.("input, textarea")) return;
      if (e.code === "Space") {
        e.preventDefault();
        fireNext();
      } else if (e.key === "Escape") {
        stopPitch();
      } else if (e.key === "1") go("counter");
      else if (e.key === "2") go("scoreboard");
      else if (e.key === "3") go("pruning");
      else if (e.key === "4") go("privacy");
      else if (e.key === "5") go("close");
      else if (e.key === "p" || e.key === "P") {
        if (pitching) stopPitch();
        else startPitch();
      } else if (e.key === "n" || e.key === "N") {
        setNotesOn((v) => !v);
      } else if (e.key === "a" || e.key === "A") {
        playRef.current = !playRef.current;
        setPlaying(playRef.current);
        if (playRef.current) {
          go("counter");
          fireNext();
        }
      } else if (e.key === "r" || e.key === "R") {
        playRef.current = false;
        setPlaying(false);
        stopPitch();
        resetDemo().then(() => {
          setEvent(null);
          setBeat(null);
          setNote("");
        });
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pitching]);

  return (
    <div className="min-h-screen">
      {screen === "counter" && (
        <Counter merchant={merchant} event={event} onAdvance={fireNext} beat={beat} />
      )}
      {screen === "scoreboard" && <Scoreboard />}
      {screen === "pruning" && <Pruning />}
      {screen === "privacy" && <Privacy />}
      {screen === "close" && <Close />}

      {pitching && (
        <p className="pointer-events-none fixed right-6 top-6 font-mono text-[12px] text-ink/40">
          {fmt(elapsed)} / 3:00
        </p>
      )}

      {notesOn && note && (
        <p className="pointer-events-none fixed bottom-14 left-6 right-6 mx-auto max-w-xl text-center text-[13px] leading-relaxed text-ink/55">
          {note}
        </p>
      )}

      <div className="pointer-events-none fixed bottom-4 left-0 right-0 flex justify-center">
        <p className="text-[11px] tracking-wide text-ink/40">
          {SCREENS.map((s, i) => (
            <span key={s} className={screen === s ? "text-ink/70" : ""}>
              {i + 1} {s}
              {i < SCREENS.length - 1 ? "  ·  " : ""}
            </span>
          ))}
          <span className="ml-4">space · next</span>
          <span className={`ml-4 ${pitching ? "text-saffron" : ""}`}>p · 3-min pitch</span>
          <span className="ml-4">n · notes</span>
          <span className={`ml-4 ${playing ? "text-saffron" : ""}`}>a · autoplay</span>
          <span className="ml-4">r · reset</span>
        </p>
      </div>
    </div>
  );
}
