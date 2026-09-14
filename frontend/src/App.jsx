import { useEffect, useState } from "react";
import { getMerchant, nextPayment, resetDemo, speakAmount } from "./api.js";
import Counter from "./screens/Counter.jsx";
import Scoreboard from "./screens/Scoreboard.jsx";
import Pruning from "./screens/Pruning.jsx";

const SCREENS = ["counter", "scoreboard", "pruning"];

export default function App() {
  const [screen, setScreen] = useState(() => {
    const h = window.location.hash.replace("#", "");
    return SCREENS.includes(h) ? h : "counter";
  });
  const [merchant, setMerchant] = useState(null);
  const [event, setEvent] = useState(null);
  const [busy, setBusy] = useState(false);

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
    if (busy) return;
    setBusy(true);
    try {
      const data = await nextPayment();
      setEvent(data);
      if (data.announcement) speakAmount(data.announcement);
    } finally {
      setTimeout(() => setBusy(false), 400);
    }
  }

  useEffect(() => {
    function onKey(e) {
      if (e.target?.matches?.("input, textarea")) return;
      if (e.code === "Space") {
        e.preventDefault();
        fireNext();
      } else if (e.key === "1") {
        setScreen("counter");
        window.location.hash = "counter";
      } else if (e.key === "2") {
        setScreen("scoreboard");
        window.location.hash = "scoreboard";
      } else if (e.key === "3") {
        setScreen("pruning");
        window.location.hash = "pruning";
      } else if (e.key === "r" || e.key === "R") {
        resetDemo().then(() => setEvent(null));
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [busy]);

  return (
    <div className="min-h-screen">
      {screen === "counter" && (
        <Counter merchant={merchant} event={event} onAdvance={fireNext} />
      )}
      {screen === "scoreboard" && <Scoreboard />}
      {screen === "pruning" && <Pruning />}

      <div className="pointer-events-none fixed bottom-4 left-0 right-0 flex justify-center">
        <p className="text-[11px] tracking-wide text-ink/40">
          {SCREENS.map((s, i) => (
            <span key={s} className={screen === s ? "text-ink/70" : ""}>
              {i + 1} {s}
              {i < 2 ? "  ·  " : ""}
            </span>
          ))}
          <span className="ml-4">space · next payment</span>
          <span className="ml-4">r · reset</span>
        </p>
      </div>
    </div>
  );
}
