import { useEffect, useState } from "react";
import { getBudget, getModel } from "../api.js";

export default function Pruning() {
  const [budget, setBudget] = useState(null);
  const [model, setModel] = useState(null);

  useEffect(() => {
    getBudget().then(setBudget).catch(() => {});
    getModel().then(setModel).catch(() => {});
  }, []);

  if (!budget) return <p className="p-16 text-ink/50">Loading bandit state…</p>;

  return (
    <div className="mx-auto min-h-screen max-w-3xl px-6 pb-20 pt-10">
      <p className="text-[11px] font-medium uppercase tracking-[0.22em] text-ink/45">
        Cue budget
      </p>
      <h1 className="deva mt-1 text-3xl font-semibold">कम दिखाओ तो चले</h1>
      <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink/55">
        An AI that reduces its own output. Hard cap of {budget.daily_cap} cues a day,
        allocated by whether this shopkeeper actually acts.
      </p>

      <p className="display mt-8 text-4xl text-indigo">
        {budget.now_per_day}
        <span className="text-2xl text-ink/35"> / day now</span>
        <span className="mx-3 text-2xl text-ink/25">not</span>
        <span className="text-ink/40 line-through">{budget.unconstrained_per_day}</span>
      </p>
      {budget.message && <p className="deva mt-3 text-sm text-ink/60">{budget.message}</p>}

      <ul className="mt-10 divide-y divide-ink/10 border-y border-ink/10">
        {budget.types.map((t) => (
          <li key={t.type} className={`flex items-center justify-between py-5 ${t.pruned ? "opacity-45" : ""}`}>
            <div>
              <p className={`deva text-xl font-medium ${t.pruned ? "line-through" : ""}`}>{t.hi}</p>
              <p className={`text-sm text-ink/50 ${t.pruned ? "line-through" : ""}`}>{t.en}</p>
              {t.pruned && (
                <p className="mt-1 text-[12px] text-saffron">I stopped showing you this one.</p>
              )}
            </div>
            <div className="text-right">
              <p className="display text-2xl">{Math.round(t.action_rate * 100)}%</p>
              <p className="text-[11px] text-ink/40">
                acted {t.rewards}/{t.pulls}
              </p>
            </div>
          </li>
        ))}
      </ul>

      {model && (
        <div className="mt-10 rounded-2xl bg-white/40 p-5 ring-1 ring-ink/10">
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-ink/45">
            Return-propensity model — printable
          </p>
          <p className="mt-2 text-[12px] leading-relaxed text-ink/50">{model.note}</p>
          <dl className="mt-4 grid grid-cols-2 gap-2 text-[12px] sm:grid-cols-3">
            <Coef k="intercept" v={model.intercept} />
            <Coef k="ticket" v={model.w_ticket} />
            <Coef k="hour" v={model.w_hour} />
            <Coef k="day of week" v={model.w_dow} />
            <Coef k="weekend" v={model.w_weekend} />
            <Coef k="threshold" v={model.threshold} />
          </dl>
        </div>
      )}
    </div>
  );
}

function Coef({ k, v }) {
  return (
    <div className="rounded-lg bg-paper px-3 py-2">
      <dt className="text-ink/40">{k}</dt>
      <dd className="font-medium tabular-nums">{v}</dd>
    </div>
  );
}
