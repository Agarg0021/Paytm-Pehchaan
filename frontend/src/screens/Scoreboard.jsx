import { useEffect, useMemo, useState } from "react";
import { getScoreboard } from "../api.js";

function rupees(n) {
  return `₹${Number(n).toLocaleString("en-IN")}`;
}

export default function Scoreboard() {
  const [firstTimers, setFirstTimers] = useState(45);
  const [avgSpend, setAvgSpend] = useState(1850);
  const [actedOverride, setActedOverride] = useState(0.41);
  const [ctrlOverride, setCtrlOverride] = useState(0.23);
  const [data, setData] = useState(null);

  const params = useMemo(() => {
    const p = {
      first_timers: firstTimers,
      avg_spend: avgSpend,
    };
    if (actedOverride != null) p.acted_rate = actedOverride;
    if (ctrlOverride != null) p.control_rate = ctrlOverride;
    return p;
  }, [firstTimers, avgSpend, actedOverride, ctrlOverride]);

  useEffect(() => {
    getScoreboard(params).then(setData).catch(() => {});
  }, [params]);

  if (!data) {
    return <p className="p-16 text-ink/50">Measuring the holdout…</p>;
  }

  const actedPct = Math.round(data.used.acted_rate * 100);
  const ctrlPct = Math.round(data.used.control_rate * 100);
  const max = Math.max(actedPct, ctrlPct, 50);

  return (
    <div className="mx-auto min-h-screen max-w-4xl px-6 pb-20 pt-10">
      <p className="text-[11px] font-medium uppercase tracking-[0.22em] text-ink/45">
        Closed loop
      </p>
      <h1 className="deva mt-1 text-3xl font-semibold">क्या फ़र्क पड़ा</h1>
      <p className="mt-1 text-sm text-ink/55">Did greeting a first-timer change whether they came back?</p>

      <div className="mt-10 grid gap-10 md:grid-cols-[1.3fr_0.9fr]">
        <div>
          <Bar
            label="मैंने बात की"
            sub={`acted · n = ${data.acted.n}`}
            pct={actedPct}
            max={max}
            color="#2D3A72"
          />
          <div className="mt-8">
            <Bar
              label="कुछ नहीं कहा"
              sub={`not acted · n = ${data.not_acted.n}`}
              pct={ctrlPct}
              max={max}
              color="#8a8175"
            />
          </div>

          <div className="mt-10 flex items-end gap-6 border-t border-ink/10 pt-6">
            <Stat k="gap" v={`+${data.gap_pp} pp`} />
            <Stat k="extra regulars / month" v={`+${data.extra_regulars}`} />
            <Stat k="new monthly revenue" v={rupees(data.rupee_value)} big />
          </div>
        </div>

        <aside className="rounded-2xl bg-white/50 p-5 ring-1 ring-ink/10">
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-ink/45">
            Assumptions — not hidden
          </p>
          <Slider
            label="First-timers / month"
            value={firstTimers}
            min={10}
            max={90}
            onChange={setFirstTimers}
          />
          <Slider
            label="Avg regular monthly spend"
            value={avgSpend}
            min={500}
            max={4000}
            step={50}
            format={rupees}
            onChange={setAvgSpend}
          />
          <Slider
            label="Return rate if greeted"
            value={Math.round((actedOverride ?? data.acted.rate) * 100)}
            min={10}
            max={70}
            format={(n) => `${n}%`}
            onChange={(n) => setActedOverride(n / 100)}
          />
          <Slider
            label="Return rate if ignored"
            value={Math.round((ctrlOverride ?? data.not_acted.rate) * 100)}
            min={5}
            max={50}
            format={(n) => `${n}%`}
            onChange={(n) => setCtrlOverride(n / 100)}
          />
          <p className="mt-4 text-[11px] leading-relaxed text-ink/45">{data.note}</p>
          <p className="mt-2 text-[11px] text-ink/40">
            Measured on this stream: {Math.round(data.acted.rate * 100)}% vs {Math.round(data.not_acted.rate * 100)}%.
            Sliders start at the pitch assumptions (41% / 23%).
          </p>
        </aside>
      </div>
    </div>
  );
}

function Bar({ label, sub, pct, max, color }) {
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <div>
          <p className="deva text-lg font-medium">{label}</p>
          <p className="text-[11px] text-ink/45">{sub}</p>
        </div>
        <p className="display text-4xl" style={{ color }}>
          {pct}%
        </p>
      </div>
      <div className="mt-3 h-9 overflow-hidden rounded-md bg-ink/8">
        <div
          className="h-full"
          style={{ width: `${(pct / max) * 100}%`, background: color }}
        />
      </div>
      <p className="mt-1 text-[11px] text-ink/40">14-day return rate</p>
    </div>
  );
}

function Stat({ k, v, big }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide text-ink/40">{k}</p>
      <p className={`mt-1 font-semibold ${big ? "display text-3xl text-indigo" : "text-xl"}`}>{v}</p>
    </div>
  );
}

function Slider({ label, value, min, max, step = 1, onChange, format }) {
  return (
    <label className="mt-5 block">
      <span className="flex justify-between text-[12px]">
        <span className="text-ink/60">{label}</span>
        <span className="font-medium">{format ? format(value) : value}</span>
      </span>
      <input
        className="mt-2 w-full"
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </label>
  );
}
