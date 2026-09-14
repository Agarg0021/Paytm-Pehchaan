import { useEffect, useState } from "react";
import { actOnCue } from "../api.js";

const COACH = {
  PEHLI_BAAR: "Say your name. Mention you deliver.",
  LAUT_AAYE: "Ask where they've been.",
  RUK_GAYE: "Catch them before they're gone.",
  KHAAS_GRAHAK: "Treat them like it.",
};

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

function cadenceLine(event, cue) {
  const c = event.cadence;
  if (!c) return null;
  if (cue?.type === "PEHLI_BAAR" && cue.propensity != null && event.threshold != null) {
    return `p(return 14d) ${cue.propensity.toFixed(2)} ≥ ${event.threshold} · not all first-timers`;
  }
  if (c.mean != null && c.bar != null && c.gap_days != null) {
    return `gap ${c.gap_days}d · their mean ${c.mean}d · bar mean+2σ ${c.bar}d`;
  }
  return null;
}

export default function Soundbox({ event, onAdvance, beat }) {
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
  const math = event && cue ? cadenceLine(event, cue) : null;

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
        className="relative w-[360px] rounded-[36px] p-[14px] pt-[16px] sm:w-[400px]"
        style={{
          background: "linear-gradient(180deg, #fbfaf6 0%, #ece8e0 55%, #ddd6cb 100%)",
          boxShadow:
            "0 1px 0 rgba(255,255,255,0.8) inset, 0 18px 40px rgba(40,28,12,0.22), 0 2px 4px rgba(40,28,12,0.18)",
        }}
      >
        <div className="mb-2 flex items-center justify-between px-2">
          <div className="flex items-center gap-2">
            <span className={`h-2 w-2 rounded-full bg-emerald-600 ${event ? "led-live" : "opacity-40"}`} />
            <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-ink/45">
              AI Soundbox
            </span>
          </div>
          <Waveform live={!!event || beat === "two-seconds"} />
        </div>

        <div
          className="mb-2 rounded-[14px] px-4 py-2.5"
          style={{
            background: "#2a2a28",
            boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.05)",
          }}
        >
          <div className="flex items-center justify-between">
            <p className="text-[9px] uppercase tracking-[0.16em] text-white/35">customer face</p>
            <p className="display text-lg text-white/90">
              {event ? rupees(event.amount) : beat === "two-seconds" ? "₹250" : "—"}
            </p>
          </div>
          <p className="text-[10px] text-white/28">amount only · cue never shown here</p>
        </div>

        <div
          className="relative overflow-hidden rounded-[22px] px-5 py-5"
          style={{
            background: "#1A1A18",
            minHeight: 420,
            boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.06), inset 0 20px 40px rgba(0,0,0,0.35)",
          }}
        >
          <div className="flex items-start justify-between text-[11px] text-white/40">
            <span className="deva tracking-wide">पहचान · merchant</span>
            <span>{time}</span>
          </div>

          {!event && beat === "two-seconds" && (
            <div className="mt-10">
              <p className="text-[11px] uppercase tracking-[0.2em] text-white/35">Paytm par prapt hue</p>
              <p className="display mt-2 text-5xl text-white">₹250</p>
              <p className="deva mt-2 text-sm text-white/45">रुपये प्राप्त हुए</p>
              <div className="mt-10 rounded-xl border border-dashed border-white/20 px-4 py-8 text-center">
                <p className="text-[11px] uppercase tracking-[0.18em] text-white/30">empty</p>
                <p className="mt-2 text-sm text-white/50">the most underused two seconds in Indian retail</p>
              </div>
            </div>
          )}

          {!event && beat !== "two-seconds" && (
            <div className="mt-14 text-center">
              <p className="text-[11px] uppercase tracking-[0.22em] text-white/30">today</p>
              <div className="mt-5 flex items-end justify-center gap-10">
                <div>
                  <p className="display text-6xl text-white">60</p>
                  <p className="mt-1 text-[11px] text-white/40">paid him</p>
                </div>
                <div>
                  <p className="display text-6xl text-white/55">4</p>
                  <p className="mt-1 text-[11px] text-white/40">he can name</p>
                </div>
              </div>
              <p className="deva mt-8 text-lg text-white/55">इंतज़ार</p>
            </div>
          )}

          {event && (
            <div className="mt-6 text-center amount-hit">
              <p className="text-[11px] uppercase tracking-[0.2em] text-white/35">Paytm par prapt hue</p>
              <p className="display mt-2 text-5xl text-white">{rupees(event.amount)}</p>
              <p className="deva mt-2 text-sm text-white/45">रुपये प्राप्त हुए</p>
            </div>
          )}

          {event && !event.cue && (
            <p className="absolute bottom-6 left-0 right-0 text-center text-[12px] text-white/28">
              {event.opted_out ? "opted out — no cue" : "no cue — most payments get nothing"}
            </p>
          )}

          {cue && (
            <div
              className="cue-in absolute bottom-4 left-4 right-4 rounded-2xl px-4 py-3.5"
              style={{
                background: "#F3F0EA",
                boxShadow: `0 0 0 2px ${accent}`,
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <p className="text-[10px] font-medium uppercase tracking-[0.16em]" style={{ color: accent }}>
                {saffron ? "highest leverage" : "for your eyes only"}
              </p>
              <p className="deva mt-1 text-[26px] font-semibold leading-tight text-ink">{cue.hi}</p>
              <p className="text-sm text-ink/55">{cue.en}</p>
              <p className="mt-1.5 text-[12px] leading-snug text-ink/70">{cue.why_en}</p>
              {math && (
                <p className="mt-1 font-mono text-[10px] leading-snug text-ink/40">{math}</p>
              )}
              <p className="mt-1.5 text-[12px] italic text-ink/60">{COACH[cue.type]}</p>
              {event.token_tail && (
                <p className="mt-1.5 font-mono text-[10px] tracking-wide text-ink/35">
                  token · {event.token_tail} · this shop only
                </p>
              )}
              <button
                type="button"
                onClick={greet}
                className="mt-2.5 w-full rounded-xl py-2.5 text-sm font-medium text-white"
                style={{ background: accent, opacity: acted ? 0.55 : 1 }}
              >
                {acted ? "दर्ज · noted" : "मैंने बात की  ·  I greeted them"}
              </button>
            </div>
          )}
        </div>

        <div className="mt-3 flex items-center justify-between px-2 pb-1">
          <p className="text-[10px] text-ink/40">cue never spoken</p>
          <p className="text-[10px] font-medium tracking-wide text-ink/50">merchant screen</p>
        </div>
      </div>
    </div>
  );
}

function Waveform({ live }) {
  return (
    <div className={`flex h-[14px] items-center ${live ? "wave-live" : ""}`} aria-hidden>
      {Array.from({ length: 7 }).map((_, i) => (
        <span
          key={i}
          className="wave-bar"
          style={{ animationDelay: live ? `${i * 70}ms` : undefined }}
        />
      ))}
    </div>
  );
}
