import { useEffect, useState } from "react";
import { actOnCue } from "../api.js";

function rupees(n) {
  return `₹${Number(n).toLocaleString("en-IN")}`;
}

function clock() {
  return new Date().toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export default function Soundbox({ event, onAdvance }) {
  const [cue, setCue] = useState(null);
  const [acted, setActed] = useState(false);
  const [time, setTime] = useState(clock);

  useEffect(() => {
    const t = setInterval(() => setTime(clock()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    setActed(false);
    if (!event) {
      setCue(null);
      return;
    }
    setCue(null);
    if (!event.cue) return;
    const id = setTimeout(() => setCue(event.cue), 0);
    return () => clearTimeout(id);
  }, [event]);

  async function greet() {
    if (!cue || acted) return;
    await actOnCue(cue.id);
    setActed(true);
  }

  const saffron = cue?.type === "PEHLI_BAAR";
  const accent = saffron ? "#C8761A" : "#2D3A72";

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onAdvance}
      onKeyDown={(e) => {
        if (e.key === "Enter") onAdvance();
      }}
      className="relative mx-auto block cursor-pointer text-left"
      aria-label="Advance payment"
    >
      <div
        className="relative w-[360px] rounded-[36px] p-[14px] pt-[18px] sm:w-[400px]"
        style={{
          background: "linear-gradient(180deg, #fbfaf6 0%, #ece8e0 55%, #ddd6cb 100%)",
          boxShadow:
            "0 1px 0 rgba(255,255,255,0.8) inset, 0 18px 40px rgba(40,28,12,0.22), 0 2px 4px rgba(40,28,12,0.18)",
        }}
      >
        <div className="mb-3 flex items-center justify-between px-2">
          <div className="flex items-center gap-2">
            <span className={`h-2 w-2 rounded-full bg-emerald-600 ${event ? "led-live" : "opacity-40"}`} />
            <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-ink/45">
              merchant screen
            </span>
          </div>
          <SpeakerGrill />
        </div>

        <div
          className="relative overflow-hidden rounded-[22px] px-5 py-5"
          style={{
            background: "#1A1A18",
            minHeight: 430,
            boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.06), inset 0 20px 40px rgba(0,0,0,0.35)",
          }}
        >
          <div className="flex items-start justify-between text-[11px] text-white/40">
            <span className="deva tracking-wide">पहचान</span>
            <span>{time}</span>
          </div>

          {!event && (
            <div className="mt-24 text-center">
              <p className="text-[11px] uppercase tracking-[0.22em] text-white/30">waiting</p>
              <p className="deva mt-3 text-2xl font-medium text-white/80">इंतज़ार</p>
              <p className="mt-2 text-sm text-white/35">next payment lands here</p>
            </div>
          )}

          {event && (
            <div className="mt-8 text-center amount-hit">
              <p className="text-[11px] uppercase tracking-[0.2em] text-white/35">Paytm par prapt hue</p>
              <p className="display mt-2 text-5xl text-white">{rupees(event.amount)}</p>
              <p className="deva mt-2 text-sm text-white/45">रुपये प्राप्त हुए</p>
            </div>
          )}

          {event && !event.cue && (
            <p className="absolute bottom-6 left-0 right-0 text-center text-[12px] text-white/28">
              no cue — most payments get nothing
            </p>
          )}

          {cue && (
            <div
              className="cue-in absolute bottom-4 left-4 right-4 rounded-2xl px-4 py-4"
              style={{
                background: "#F3F0EA",
                boxShadow: `0 0 0 2px ${accent}`,
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <p className="text-[10px] font-medium uppercase tracking-[0.16em]" style={{ color: accent }}>
                {saffron ? "highest leverage" : "for your eyes only"}
              </p>
              <p className="deva mt-1 text-[28px] font-semibold leading-tight text-ink">{cue.hi}</p>
              <p className="text-sm text-ink/55">{cue.en}</p>
              <p className="mt-2 text-[12px] leading-snug text-ink/70">{cue.why_en}</p>
              <p className="deva text-[12px] text-ink/55">{cue.why_hi}</p>
              <button
                type="button"
                onClick={greet}
                className="mt-3 w-full rounded-xl py-2.5 text-sm font-medium text-white"
                style={{ background: accent, opacity: acted ? 0.55 : 1 }}
              >
                {acted ? "दर्ज · noted" : "मैंने बात की  ·  I greeted them"}
              </button>
            </div>
          )}
        </div>

        <div className="mt-3 flex items-center justify-between px-2 pb-1">
          <p className="text-[10px] text-ink/40">cue never spoken</p>
          <p className="text-[10px] font-medium tracking-wide text-ink/50">AI Soundbox</p>
        </div>
      </div>
    </div>
  );
}

function SpeakerGrill() {
  return (
    <div className="flex gap-[3px]" aria-hidden>
      {Array.from({ length: 5 }).map((_, i) => (
        <span key={i} className="h-2 w-2 rounded-full bg-ink/20" />
      ))}
    </div>
  );
}
