from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta

import numpy as np

from db import DB_PATH, executemany, fetchall, fetchone, init_schema, run
from engine import LogisticPropensity, cadence_from_prior, decide_cue

SEED = 42
MERCHANT_NAME = "Verma Kirana Store"
LOCALITY = "Laxmi Nagar"
CITY = "Delhi"
SALT_MATERIAL = b"verma-kirana-laxmi-nagar-pehchaan"
DEMO_DAY = datetime(2026, 9, 14, 10, 0, 0)
N_DAYS = 90
N_PAYERS = 416  # + 4 personas = 420
DAILY_CAP = 4
ACTED_RETURN_P = 0.41
CONTROL_RETURN_P = 0.23

PERSONA_HANDLES = {
    "first_timer": "synth:verma:first-timer-demo",
    "returner": "synth:verma:returner-7wk",
    "top_decile": "synth:verma:top-decile",
    "broken_rhythm": "synth:verma:broken-rhythm",
    "ordinary": "synth:verma:ordinary-regular",
}


def merchant_hash(handle: str, salt: bytes) -> str:
    digest = hmac.new(salt, handle.encode(), hashlib.sha256).hexdigest()
    return digest[:16]


def _hour(rng: np.random.Generator) -> int:
    # Kirana peaks: morning household + evening rush.
    return int(rng.choice(
        [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21],
        p=[0.04, 0.10, 0.12, 0.11, 0.08, 0.05, 0.04, 0.04, 0.05, 0.06, 0.08, 0.10, 0.07, 0.04, 0.02],
    ))


def _stamp(day_offset: float, hour: int, minute: int, second: int) -> datetime:
    start = datetime(2026, 6, 16, 0, 0, 0)
    return start + timedelta(days=int(day_offset), hours=hour, minutes=minute, seconds=second)


def generate(force: bool = False) -> None:
    init_schema()
    existing = fetchone("SELECT COUNT(*) FROM payments")
    if existing and existing[0] > 0 and not force:
        return
    if force and DB_PATH.exists():
        run("DROP TABLE IF EXISTS merchant")
        for t in [
            "payers",
            "payments",
            "cues",
            "actions",
            "outcomes",
            "bandit",
            "model",
            "demo_script",
            "settings",
        ]:
            run(f"DROP TABLE IF EXISTS {t}")
        run("DROP SEQUENCE IF EXISTS seq_payment")
        run("DROP SEQUENCE IF EXISTS seq_cue")
        run("DROP SEQUENCE IF EXISTS seq_action")
        init_schema()

    rng = np.random.default_rng(SEED)
    salt = hmac.new(SALT_MATERIAL, str(SEED).encode(), hashlib.sha256).digest()

    run("DELETE FROM merchant")
    run(
        "INSERT INTO merchant VALUES (1, ?, ?, ?, ?)",
        [MERCHANT_NAME, LOCALITY, CITY, salt.hex()],
    )

    payers: list[dict] = []
    payments: list[tuple] = []

    def add_payer(handle: str, cadence_mean: float, cadence_std: float, ticket_mean: float, persona: str | None):
        h = merchant_hash(handle, salt)
        payers.append(
            {
                "hash": h,
                "cadence_mean": cadence_mean,
                "cadence_std": cadence_std,
                "ticket_mean": ticket_mean,
                "persona": persona,
                "handle": handle,
            }
        )
        return h

    # --- planted personas (history) -----------------------------------------
    first_h = add_payer(PERSONA_HANDLES["first_timer"], 0, 0, 240, "first_timer")
    ret_h = add_payer(PERSONA_HANDLES["returner"], 7.0, 0.8, 320, "returner")
    top_h = add_payer(PERSONA_HANDLES["top_decile"], 3.0, 0.5, 820, "top_decile")
    brk_h = add_payer(PERSONA_HANDLES["broken_rhythm"], 4.5, 0.7, 180, "broken_rhythm")
    ord_h = add_payer(PERSONA_HANDLES["ordinary"], 2.2, 0.5, 140, "ordinary")

    pid = 1

    def push_pay(payer_hash: str, ts: datetime, amount: int):
        nonlocal pid
        payments.append((pid, payer_hash, int(amount), ts, ts.hour, ts.weekday(), False))
        pid += 1

    def ticket(mean: float) -> int:
        val = rng.lognormal(np.log(max(mean, 40)), 0.28)
        return int(np.clip(val, 20, 2500))

    # Returner: weekly visits for ~6 weeks, then 7 weeks of silence.
    for week in range(7):
        day = 2 + week * 7 + float(rng.normal(0, 0.25))
        hour = 11
        ts = _stamp(day, hour, int(rng.integers(0, 40)), int(rng.integers(0, 50)))
        push_pay(ret_h, ts, ticket(320))

    # Top decile: frequent, high ticket, through yesterday.
    d = 1.0
    while d < N_DAYS - 0.5:
        ts = _stamp(d, _hour(rng), int(rng.integers(0, 50)), int(rng.integers(0, 50)))
        push_pay(top_h, ts, ticket(820))
        d += max(1.6, rng.normal(3.0, 0.45))

    # Broken rhythm: every ~4.5 days until ~14 days ago, then silence.
    d = 1.5
    while d < N_DAYS - 14:
        ts = _stamp(d, _hour(rng), int(rng.integers(0, 50)), int(rng.integers(0, 50)))
        push_pay(brk_h, ts, ticket(180))
        d += max(2.5, rng.normal(4.5, 0.6))

    # Ordinary regular: weekly-ish, last seen yesterday — on cadence, not top-decile.
    for week in range(12):
        day = 4 + week * 7
        if day >= N_DAYS - 1:
            break
        ts = _stamp(day, 18, int(rng.integers(0, 40)), int(rng.integers(0, 40)))
        push_pay(ord_h, ts, ticket(140))
    push_pay(ord_h, _stamp(N_DAYS - 1, 19, 10, 0), ticket(95))

    # --- population ----------------------------------------------------------
    # Mix calibrated to ~60 payments/day across 90 days.
    segments = (
        [(40, 2.1, 0.5, 95)]      # near-daily milk/bread
        + [(180, 7.0, 1.1, 210)]  # weekly
        + [(110, 14.0, 2.2, 380)] # fortnightly ration
        + [(86, 28.0, 4.0, 620)]  # monthly
    )
    handle_i = 0
    for count, mean, std, tmean in segments:
        for _ in range(count):
            handle_i += 1
            h = add_payer(f"synth:verma:p{handle_i:04d}", mean, std, tmean, None)
            gap_returner = handle_i <= 48 and 6.0 <= mean <= 8.0
            if rng.random() < 0.32:
                start = float(rng.uniform(8, N_DAYS - 16))
            else:
                start = float(rng.uniform(-mean * 2, 4))
            d = start
            while d < N_DAYS - 0.4:
                if gap_returner and 36 < d < 78:
                    d += max(mean * 0.35, rng.normal(mean, std))
                    continue
                if d >= 0:
                    hour = _hour(rng)
                    ts = _stamp(d, hour, int(rng.integers(0, 55)), int(rng.integers(0, 55)))
                    push_pay(h, ts, ticket(tmean))
                d += max(mean * 0.35, rng.normal(mean, std))

    payments.sort(key=lambda r: r[3])
    # Re-number in time order.
    payments = [
        (i + 1, p[1], p[2], p[3], p[4], p[5], p[6]) for i, p in enumerate(payments)
    ]

    executemany(
        "INSERT INTO payers VALUES (?, ?, ?, ?, ?)",
        [(p["hash"], p["cadence_mean"], p["cadence_std"], p["ticket_mean"], p["persona"]) for p in payers],
    )
    executemany(
        "INSERT INTO payments VALUES (?, ?, ?, ?, ?, ?, ?)",
        payments,
    )

    # Spend percentiles over the 90-day window (all historical payments).
    spend_rows = fetchall(
        "SELECT payer_hash, SUM(amount) FROM payments GROUP BY payer_hash"
    )
    spend_map = {h: s for h, s in spend_rows}
    spends = np.array(list(spend_map.values()), dtype=float)
    def percentile_of(h: str) -> float:
        s = spend_map.get(h, 0)
        return float((spends <= s).mean() * 100)

    # Fit return-propensity on first payments that have a 14-day observation window.
    by_payer: dict[str, list[datetime]] = {}
    first_events = []  # (ticket, hour, dow, weekend, returned, cueable)
    cutoff = DEMO_DAY - timedelta(days=14)

    # Walk to collect first payments and a synthetic return label from a known process,
    # then overwrite cued outcomes later so the scoreboard matches the experiment.
    seen = set()
    for _id, h, amount, ts, hour, dow, _live in payments:
        if h in seen:
            continue
        seen.add(h)
        weekend = 1 if dow >= 5 else 0
        # Latent return process — the model has something real to fit.
        logit = (
            -1.55
            + 0.0022 * amount
            + 0.42 * (1.0 if 8 <= hour <= 12 else 0.0)
            + 0.28 * (1.0 if dow < 5 else 0.0)
        )
        p = 1 / (1 + np.exp(-logit))
        returned = 1 if rng.random() < p else 0
        first_events.append((h, amount, hour, dow, weekend, returned, ts))

    train = [e for e in first_events if e[6] <= cutoff]
    model = LogisticPropensity()
    model.fit(
        [(e[1], e[2], e[3], e[4]) for e in train],
        [e[5] for e in train],
    )
    # Guarantee the planted first-timer clears the bar (Tue 10:00, ₹240).
    planted_p = model.predict_proba(240, 10, 0, 0)  # demo beat: Mon 10:00, ₹240
    if planted_p < model.threshold:
        model.threshold = max(0.12, planted_p - 0.04)

    run("DELETE FROM model")
    run(
        "INSERT INTO model VALUES (?, ?, ?, ?, ?, ?)",
        [
            float(model.w[0]),
            float(model.w[1]),
            float(model.w[2]),
            float(model.w[3]),
            float(model.w[4]),
            float(model.threshold),
        ],
    )

    bandit = {
        t: {"pulls": 0, "rewards": 0, "pruned": False, "prune_reason": None}
        for t in ["PEHLI_BAAR", "LAUT_AAYE", "KHAAS_GRAHAK", "RUK_GAYE"]
    }
    # Historical merchant behaviour — khaas is ignored, first-timers are acted on.
    act_p = {
        "PEHLI_BAAR": 0.72,
        "LAUT_AAYE": 0.58,
        "RUK_GAYE": 0.44,
        "KHAAS_GRAHAK": 0.02,
    }

    # Action-rate prior so the live bandit prefers types he uses.
    # (pulls/rewards accumulate from the walk below.)

    cues = []
    actions = []
    outcomes = []
    cue_id = 1
    action_id = 1
    day_counts: dict[str, int] = {}
    unconstrained = 0

    last_khaas: dict[str, datetime] = {}
    for _id, h, amount, ts, hour, dow, _live in payments:
        prior = by_payer.get(h, [])
        cad = cadence_from_prior(prior, ts, spend_map.get(h, 0), percentile_of(h))
        prop = None
        if cad.n_prior == 0:
            prop = model.predict_proba(amount, hour, dow, 1 if dow >= 5 else 0)
        cue = decide_cue(cad, prop, model.threshold)
        by_payer.setdefault(h, []).append(ts)
        if cue is None:
            continue
        if cue.cue_type == "KHAAS_GRAHAK":
            prev = last_khaas.get(h)
            if prev and (ts - prev).days < 21:
                continue
            last_khaas[h] = ts
        unconstrained += 1
        day_key = ts.date().isoformat()
        shown = day_counts.get(day_key, 0)
        # History records the unconstrained stream, capped at 12/day — the
        # number the pitch quotes before the AI started pruning.
        if shown >= 12:
            continue
        cues.append(
            (
                cue_id,
                _id,
                h,
                cue.cue_type,
                cue.why_hi,
                cue.why_en,
                ts,
                cue.propensity,
                False,
            )
        )
        bandit[cue.cue_type]["pulls"] += 1
        day_counts[day_key] = shown + 1

        acted = rng.random() < act_p[cue.cue_type]
        if acted:
            actions.append((action_id, cue_id, ts + timedelta(seconds=8)))
            action_id += 1
            bandit[cue.cue_type]["rewards"] += 1

        if cue.cue_type == "PEHLI_BAAR" and ts <= cutoff:
            p_ret = ACTED_RETURN_P if acted else CONTROL_RETURN_P
            outcomes.append((cue_id, rng.random() < p_ret))

        cue_id += 1

    # Prune the type he never acts on.
    for t, arm in bandit.items():
        rate = arm["rewards"] / arm["pulls"] if arm["pulls"] else 0
        if t == "KHAAS_GRAHAK" or (arm["pulls"] >= 25 and rate < 0.08):
            arm["pruned"] = True
            arm["prune_reason"] = "आपने इस संकेत पर कभी कार्रवाई नहीं की, इसलिए दिखाना बंद कर दिया"

    executemany(
        "INSERT INTO cues VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        cues,
    )
    if actions:
        executemany("INSERT INTO actions VALUES (?, ?, ?)", actions)
    if outcomes:
        executemany("INSERT INTO outcomes VALUES (?, ?)", outcomes)
    executemany(
        "INSERT INTO bandit VALUES (?, ?, ?, ?, ?)",
        [
            (t, arm["pulls"], arm["rewards"], arm["pruned"], arm["prune_reason"])
            for t, arm in bandit.items()
        ],
    )

    days_with_payments = fetchone("SELECT COUNT(DISTINCT CAST(ts AS DATE)) FROM payments")[0]
    unconstrained_per_day = unconstrained / max(days_with_payments, 1)
    shown_per_day = len(cues) / max(days_with_payments, 1)
    now_per_day = 3

    run("DELETE FROM settings")
    executemany(
        "INSERT INTO settings VALUES (?, ?)",
        [
            ("daily_cap", str(DAILY_CAP)),
            ("unconstrained_per_day", str(max(12, int(round(unconstrained_per_day))))),
            ("now_per_day", str(now_per_day)),
            ("demo_cursor", "0"),
            ("avg_monthly_spend", "1850"),
            ("first_timers_per_month", "45"),
            ("shown_per_day", str(round(shown_per_day, 1))),
        ],
    )

    # Demo reel — engine must fire these for the pitch.
    demo = [
        (1, ord_h, 85, 10, None, "ordinary on-cadence regular — most payments get nothing"),
        (2, first_h, 240, 10, "PEHLI_BAAR", "true first-timer"),
        (3, ret_h, 310, 11, "LAUT_AAYE", "weekly rhythm, back after 7 weeks"),
        (4, brk_h, 175, 18, "RUK_GAYE", "4–5 day rhythm, overdue ~14 days"),
        (5, ord_h, 60, 19, None, "another ordinary payment"),
    ]
    run("DELETE FROM demo_script")
    executemany(
        "INSERT INTO demo_script VALUES (?, ?, ?, ?, ?, ?)",
        demo,
    )

    # Sanity: replay demo payments against the engine (not inserted).
    for seq, h, amount, hour, expected, _note in demo:
        now = DEMO_DAY.replace(hour=hour, minute=5 + seq)
        prior_rows = fetchall(
            "SELECT ts FROM payments WHERE payer_hash = ? AND ts < ? ORDER BY ts",
            [h, now],
        )
        prior = [r[0] if isinstance(r[0], datetime) else datetime.fromisoformat(str(r[0])) for r in prior_rows]
        cad = cadence_from_prior(prior, now, spend_map.get(h, 0), percentile_of(h))
        prop = model.predict_proba(amount, hour, now.weekday(), 1 if now.weekday() >= 5 else 0) if cad.n_prior == 0 else None
        got = decide_cue(cad, prop, model.threshold)
        got_type = got.cue_type if got else None
        if got_type != expected:
            raise RuntimeError(
                f"demo beat {seq} expected {expected} got {got_type} "
                f"(n_prior={cad.n_prior} gap={cad.gap_days:.1f} mean={cad.mean} pctl={cad.spend_percentile:.1f} p={prop})"
            )


if __name__ == "__main__":
    generate(force=True)
    n = fetchone("SELECT COUNT(*) FROM payments")[0]
    p = fetchone("SELECT COUNT(*) FROM payers")[0]
    c = fetchone("SELECT COUNT(*) FROM cues")[0]
    print(f"payers={p} payments={n} cues={c}")
