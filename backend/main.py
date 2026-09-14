from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Optional

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from data_gen import DEMO_DAY, generate
from db import fetchall, fetchone, init_schema, run
from engine import (
    CUE_META,
    Cue,
    LogisticPropensity,
    allow_cue,
    cadence_from_prior,
    decide_cue,
)
from hindi import announcement

subscribers: list[asyncio.Queue] = []
rng = np.random.default_rng(7)


def _dt(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def setting(key: str, default: str | None = None) -> str | None:
    row = fetchone("SELECT v FROM settings WHERE k = ?", [key])
    if row:
        return row[0]
    return default


def set_setting(key: str, value: str) -> None:
    run(
        "INSERT INTO settings VALUES (?, ?) ON CONFLICT (k) DO UPDATE SET v = excluded.v",
        [key, value],
    )


def load_model() -> LogisticPropensity:
    row = fetchone("SELECT intercept, w_ticket, w_hour, w_dow, w_weekend, threshold FROM model")
    m = LogisticPropensity()
    if row:
        m.w = np.array(row[:5], dtype=float)
        m.threshold = float(row[5])
    return m


def load_bandit() -> dict[str, dict]:
    rows = fetchall("SELECT cue_type, pulls, rewards, pruned, prune_reason FROM bandit")
    return {
        t: {
            "pulls": pulls,
            "rewards": rewards,
            "pruned": bool(pruned),
            "prune_reason": reason,
        }
        for t, pulls, rewards, pruned, reason in rows
    }


def spend_percentile(payer_hash: str) -> tuple[float, float]:
    row = fetchone(
        "SELECT SUM(amount), (SELECT COUNT(*) FROM payers) FROM payments WHERE payer_hash = ?",
        [payer_hash],
    )
    spend = float(row[0] or 0)
    ranks = fetchone(
        """
        SELECT 100.0 * SUM(CASE WHEN s <= ? THEN 1 ELSE 0 END) / COUNT(*)
        FROM (SELECT SUM(amount) AS s FROM payments GROUP BY payer_hash)
        """,
        [spend],
    )
    return spend, float(ranks[0] if ranks and ranks[0] is not None else 0)


def next_ids() -> tuple[int, int]:
    p = fetchone("SELECT COALESCE(MAX(id), 0) + 1 FROM payments")[0]
    c = fetchone("SELECT COALESCE(MAX(id), 0) + 1 FROM cues")[0]
    return int(p), int(c)


def shown_on(day: datetime) -> int:
    row = fetchone(
        """
        SELECT COUNT(*) FROM cues
        WHERE CAST(ts AS DATE) = CAST(? AS DATE)
        """,
        [day],
    )
    return int(row[0])


def process_payment(
    payer_hash: str,
    amount: int,
    ts: datetime,
    is_live: bool = True,
    force_cue: bool = False,
    forced_type: str | None = None,
) -> dict[str, Any]:
    exists = fetchone("SELECT 1 FROM payers WHERE hash = ?", [payer_hash])
    if not exists:
        raise HTTPException(404, "unknown payer token")

    pay_id, cue_id = next_ids()
    run(
        "INSERT INTO payments VALUES (?, ?, ?, ?, ?, ?, ?)",
        [pay_id, payer_hash, int(amount), ts, ts.hour, ts.weekday(), is_live],
    )

    prior_rows = fetchall(
        "SELECT ts FROM payments WHERE payer_hash = ? AND id != ? ORDER BY ts",
        [payer_hash, pay_id],
    )
    prior = [_dt(r[0]) for r in prior_rows]
    spend, pctl = spend_percentile(payer_hash)
    cad = cadence_from_prior(prior, ts, spend, pctl)

    model = load_model()
    prop = None
    if cad.n_prior == 0:
        prop = model.predict_proba(amount, ts.hour, ts.weekday(), 1 if ts.weekday() >= 5 else 0)

    cue = decide_cue(cad, prop, model.threshold)
    if cue is None and forced_type:
        meta_why = {
            "PEHLI_BAAR": ("इस दुकान पर पहले कोई भुगतान नहीं", "no payment from this person before"),
            "LAUT_AAYE": ("बहुत दिनों बाद लौटे — इनके अपने रिदम से देर", "back after a long gap by their own rhythm"),
            "RUK_GAYE": ("रिदम टूट गया था", "their own visit rhythm had broken"),
            "KHAAS_GRAHAK": ("पिछले 90 दिन में सबसे ज़्यादा ख़र्च करने वाले 10% में", "top 10% by spend at this shop in 90 days"),
        }
        why = meta_why[forced_type]
        cue = Cue(forced_type, why[0], why[1], prop)
    bandit = load_bandit()
    daily_cap = int(setting("daily_cap", "4") or 4)
    shown = shown_on(ts)

    kept = None
    if cue is not None:
        ok = force_cue or allow_cue(cue.cue_type, bandit, shown, daily_cap, rng)
        if ok:
            run(
                "INSERT INTO cues VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    cue_id,
                    pay_id,
                    payer_hash,
                    cue.cue_type,
                    cue.why_hi,
                    cue.why_en,
                    ts,
                    cue.propensity,
                    is_live,
                ],
            )
            run(
                "UPDATE bandit SET pulls = pulls + 1 WHERE cue_type = ?",
                [cue.cue_type],
            )
            kept = cue
            kept_id = cue_id
        else:
            kept_id = None
    else:
        kept_id = None

    event = {
        "payment_id": pay_id,
        "payer_hash": payer_hash,
        "amount": int(amount),
        "ts": ts.isoformat(),
        "announcement": announcement(int(amount)),
        "cue": None
        if kept is None
        else {
            "id": kept_id,
            "type": kept.cue_type,
            "hi": kept.hi,
            "en": kept.en,
            "why_hi": kept.why_hi,
            "why_en": kept.why_en,
            "propensity": kept.propensity,
        },
    }
    return event


async def broadcast(event: dict) -> None:
    dead = []
    for q in subscribers:
        try:
            q.put_nowait(event)
        except Exception:
            dead.append(q)
    for q in dead:
        subscribers.remove(q)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_schema()
    generate(force=False)
    yield


app = FastAPI(title="Paytm Pehchaan", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ActBody(BaseModel):
    cue_id: int


@app.get("/health")
def health():
    n = fetchone("SELECT COUNT(*) FROM payments")[0]
    return {"ok": True, "payments": n}


@app.get("/merchant")
def merchant():
    row = fetchone("SELECT name, locality, city FROM merchant")
    return {
        "name": row[0],
        "locality": row[1],
        "city": row[2],
        "identity": "merchant-scoped salted hash — no name, no number, anywhere",
    }


@app.get("/model")
def model_view():
    return load_model().as_dict()


@app.get("/stream")
async def stream():
    q: asyncio.Queue = asyncio.Queue()
    subscribers.append(q)

    async def gen():
        try:
            yield "event: hello\ndata: {\"ok\": true}\n\n"
            while True:
                try:
                    item = await asyncio.wait_for(q.get(), timeout=20)
                    yield f"data: {json.dumps(item)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            if q in subscribers:
                subscribers.remove(q)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/demo/next")
async def demo_next():
    cursor = int(setting("demo_cursor", "0") or 0)
    rows = fetchall(
        "SELECT seq, payer_hash, amount, hour, expected_cue, note FROM demo_script ORDER BY seq"
    )
    if not rows:
        raise HTTPException(500, "demo script missing")
    seq, payer_hash, amount, hour, expected, note = rows[cursor % len(rows)]
    ts = DEMO_DAY.replace(hour=int(hour), minute=4 + seq * 3, second=int(cursor) % 50)
    # If this beat already fired this session, offset seconds so IDs stay unique.
    ts = ts + timedelta(seconds=cursor * 17)
    force = expected is not None
    event = process_payment(
        payer_hash,
        int(amount),
        ts,
        is_live=True,
        force_cue=force,
        forced_type=expected,
    )
    event["demo"] = {"seq": seq, "note": note, "index": cursor + 1, "total": len(rows)}
    set_setting("demo_cursor", str(cursor + 1))
    await broadcast(event)
    return event


@app.post("/demo/reset")
def demo_reset():
    run("DELETE FROM actions WHERE cue_id IN (SELECT id FROM cues WHERE is_live)")
    run("DELETE FROM outcomes WHERE cue_id IN (SELECT id FROM cues WHERE is_live)")
    run("DELETE FROM cues WHERE is_live")
    run("DELETE FROM payments WHERE is_live")
    set_setting("demo_cursor", "0")
    return {"ok": True}


@app.get("/cue")
def cue_lookup(payer_hash: str, amount: int = 100):
    """Return at most one cue for this opaque token, or nothing."""
    now = datetime.now()
    prior_rows = fetchall(
        "SELECT ts FROM payments WHERE payer_hash = ? ORDER BY ts",
        [payer_hash],
    )
    if fetchone("SELECT 1 FROM payers WHERE hash = ?", [payer_hash]) is None:
        raise HTTPException(404, "unknown payer token")
    prior = [_dt(r[0]) for r in prior_rows]
    spend, pctl = spend_percentile(payer_hash)
    cad = cadence_from_prior(prior, now, spend, pctl)
    model = load_model()
    prop = None
    if cad.n_prior == 0:
        prop = model.predict_proba(amount, now.hour, now.weekday(), 1 if now.weekday() >= 5 else 0)
    cue = decide_cue(cad, prop, model.threshold)
    if cue is None:
        return {"cue": None, "payer_hash": payer_hash}
    return {
        "payer_hash": payer_hash,
        "cue": {
            "type": cue.cue_type,
            "hi": cue.hi,
            "en": cue.en,
            "why_hi": cue.why_hi,
            "why_en": cue.why_en,
            "propensity": cue.propensity,
        },
    }


@app.post("/act")
def act(body: ActBody):
    cue = fetchone("SELECT id, cue_type FROM cues WHERE id = ?", [body.cue_id])
    if not cue:
        raise HTTPException(404, "cue not found")
    already = fetchone("SELECT 1 FROM actions WHERE cue_id = ?", [body.cue_id])
    if already:
        return {"ok": True, "already": True}
    aid = fetchone("SELECT COALESCE(MAX(id), 0) + 1 FROM actions")[0]
    run("INSERT INTO actions VALUES (?, ?, ?)", [aid, body.cue_id, datetime.now()])
    run("UPDATE bandit SET rewards = rewards + 1 WHERE cue_type = ?", [cue[1]])
    return {"ok": True, "already": False}


@app.get("/scoreboard")
def scoreboard(
    avg_spend: float = 1850,
    first_timers: int = 45,
    acted_rate: Optional[float] = None,
    control_rate: Optional[float] = None,
):
    row = fetchone(
        """
        SELECT
          SUM(CASE WHEN a.cue_id IS NOT NULL THEN 1 ELSE 0 END),
          SUM(CASE WHEN a.cue_id IS NOT NULL AND o.returned_14d THEN 1 ELSE 0 END),
          SUM(CASE WHEN a.cue_id IS NULL THEN 1 ELSE 0 END),
          SUM(CASE WHEN a.cue_id IS NULL AND o.returned_14d THEN 1 ELSE 0 END)
        FROM cues c
        JOIN outcomes o ON o.cue_id = c.id
        LEFT JOIN actions a ON a.cue_id = c.id
        WHERE c.cue_type = 'PEHLI_BAAR' AND c.is_live = FALSE
        """
    )
    n_act, ret_act, n_ctrl, ret_ctrl = [int(x or 0) for x in row]
    measured_acted = (ret_act / n_act) if n_act else 0.0
    measured_ctrl = (ret_ctrl / n_ctrl) if n_ctrl else 0.0
    used_acted = measured_acted if acted_rate is None else acted_rate
    used_ctrl = measured_ctrl if control_rate is None else control_rate
    gap = used_acted - used_ctrl
    extra = first_timers * gap
    rupees = extra * avg_spend
    return {
        "acted": {"n": n_act, "returned": ret_act, "rate": measured_acted},
        "not_acted": {"n": n_ctrl, "returned": ret_ctrl, "rate": measured_ctrl},
        "used": {"acted_rate": used_acted, "control_rate": used_ctrl},
        "gap_pp": round(gap * 100, 1),
        "first_timers_per_month": first_timers,
        "avg_monthly_spend": avg_spend,
        "extra_regulars": round(extra, 1),
        "rupee_value": round(rupees),
        "note": "Transaction stream is synthetic. Conversion rates are the measured holdout on that stream — sliders override the display, not the mechanism.",
    }


@app.get("/budget")
def budget():
    rows = fetchall("SELECT cue_type, pulls, rewards, pruned, prune_reason FROM bandit")
    types = []
    for t, pulls, rewards, pruned, reason in rows:
        rate = (rewards / pulls) if pulls else 0.0
        meta = CUE_META[t]
        types.append(
            {
                "type": t,
                "hi": meta["hi"],
                "en": meta["en"],
                "meaning": meta["meaning"],
                "pulls": pulls,
                "rewards": rewards,
                "action_rate": rate,
                "pruned": bool(pruned),
                "prune_reason": reason,
            }
        )
    pruned = [t for t in types if t["pruned"]]
    start = int(setting("unconstrained_per_day", "12") or 12)
    now = int(setting("now_per_day", "3") or 3)
    message = None
    if pruned:
        names = ", ".join(p["hi"] for p in pruned)
        message = f"आपने {names} पर कभी कार्रवाई नहीं की। मैंने वो दिखाना बंद कर दिया। अब {now} संकेत एक दिन में, शुरू में {start} थे।"
    return {
        "daily_cap": int(setting("daily_cap", "4") or 4),
        "unconstrained_per_day": start,
        "now_per_day": now,
        "types": types,
        "message": message,
    }
