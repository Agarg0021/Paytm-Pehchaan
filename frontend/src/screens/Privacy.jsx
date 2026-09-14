import { useEffect, useState } from "react";
import { getOptouts } from "../api.js";

export default function Privacy() {
  const [opt, setOpt] = useState(null);

  useEffect(() => {
    getOptouts().then(setOpt).catch(() => {});
  }, []);

  return (
    <div className="mx-auto min-h-screen max-w-3xl px-6 pb-20 pt-10">
      <p className="text-[11px] font-medium uppercase tracking-[0.22em] text-ink/45">
        Identity
      </p>
      <h1 className="deva mt-1 text-3xl font-semibold">नाम नहीं. नंबर नहीं.</h1>
      <p className="mt-1 text-sm text-ink/55">No name. No number. No app. Paytm already promised this. We never needed it.</p>

      <div className="mt-10 grid gap-3 sm:grid-cols-4">
        <Step n="1" title="Handle" body="stays inside the payment rail" />
        <Step n="2" title="Salted HMAC" body="computed PSP-side, scoped to this merchant" />
        <Step n="3" title="Opaque token" body="cannot travel to another shop, cannot join" />
        <Step n="4" title="One cue" body="his own history, returned to him" accent />
      </div>

      <ul className="mt-12 space-y-4 text-sm leading-relaxed text-ink/70">
        <li>
          <span className="font-medium text-ink">He learns nothing a perfect memory would not already know.</span>
          {" "}He served this person. He saw them. We are not disclosing a stranger.
        </li>
        <li>
          <span className="font-medium text-ink">Zero customer action.</span>
          {" "}No enrolment, no card, no phone number, no scan.
        </li>
        <li>
          <span className="font-medium text-ink">Paytm already sells this moment to brands.</span>
          {" "}Soundbox ads run here. We are giving the same two seconds to the shopkeeper.
        </li>
      </ul>

      {opt && (
        <div className="mt-10 rounded-2xl bg-white/50 p-5 ring-1 ring-ink/10">
          <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-ink/45">
            Customer opt-out
          </p>
          <p className="mt-2 text-sm text-ink/60">
            {opt.n} tokens at this shop asked not to be remembered. Cues skipped. Tails only — still not a person.
          </p>
          <p className="mt-3 font-mono text-[12px] tracking-wide text-ink/45">
            {opt.tails.map((t) => `· ${t}`).join("  ")}
          </p>
          <p className="mt-3 text-[11px] text-ink/40">{opt.note}</p>
        </div>
      )}
    </div>
  );
}

function Step({ n, title, body, accent }) {
  return (
    <div className={`rounded-2xl px-4 py-4 ${accent ? "bg-indigo text-white" : "bg-white/50 ring-1 ring-ink/10"}`}>
      <p className={`text-[11px] tracking-wide ${accent ? "text-white/60" : "text-ink/40"}`}>{n}</p>
      <p className="mt-1 font-semibold">{title}</p>
      <p className={`mt-1 text-[12px] leading-snug ${accent ? "text-white/75" : "text-ink/55"}`}>{body}</p>
    </div>
  );
}
