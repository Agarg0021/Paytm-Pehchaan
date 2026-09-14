from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np

CUE_META = {
    "PEHLI_BAAR": {
        "hi": "पहली बार",
        "en": "Pehli baar",
        "meaning": "First payment ever at this shop",
    },
    "LAUT_AAYE": {
        "hi": "लौट आए",
        "en": "Laut aaye",
        "meaning": "Back after a long gap, by their own rhythm",
    },
    "KHAAS_GRAHAK": {
        "hi": "ख़ास ग्राहक",
        "en": "Khaas grahak",
        "meaning": "Top decile by spend at this shop",
    },
    "RUK_GAYE": {
        "hi": "रुक गए",
        "en": "Ruk gaye",
        "meaning": "Rhythm has broken — overdue by their own pattern",
    },
}

FEATURE_NAMES = ["ticket", "hour", "dow", "weekend"]


@dataclass
class Cue:
    cue_type: str
    why_hi: str
    why_en: str
    propensity: Optional[float] = None

    @property
    def hi(self) -> str:
        return CUE_META[self.cue_type]["hi"]

    @property
    def en(self) -> str:
        return CUE_META[self.cue_type]["en"]


@dataclass
class Cadence:
    n_prior: int
    gap_days: float
    mean: Optional[float]
    std: Optional[float]
    spend_90: float
    spend_percentile: float


class LogisticPropensity:
    """Four-feature logistic regression. Coefficients stay printable."""

    def __init__(self):
        self.w = np.zeros(5)  # intercept + 4
        self.threshold = 0.35
        self.scale = np.array([500.0, 24.0, 6.0, 1.0])

    def _x(self, ticket, hour, dow, weekend) -> np.ndarray:
        raw = np.array([ticket, hour, dow, weekend], dtype=float)
        return raw / self.scale

    def fit(self, rows: list[tuple], labels: list[int], epochs: int = 600, lr: float = 0.25):
        X = np.array([self._x(*r) for r in rows], dtype=float)
        y = np.array(labels, dtype=float)
        n = len(y)
        Xb = np.column_stack([np.ones(n), X])
        w = np.zeros(5)
        for _ in range(epochs):
            z = np.clip(Xb @ w, -20, 20)
            p = 1.0 / (1.0 + np.exp(-z))
            grad = (Xb.T @ (p - y)) / n
            w -= lr * grad
        self.w = w
        proba = 1.0 / (1.0 + np.exp(-np.clip(Xb @ w, -20, 20)))
        # Flag the top ~40% of first-timers — not all of them.
        self.threshold = float(np.quantile(proba, 0.60))

    def predict_proba(self, ticket, hour, dow, weekend) -> float:
        x = self._x(ticket, hour, dow, weekend)
        z = float(self.w[0] + self.w[1:] @ x)
        return float(1.0 / (1.0 + np.exp(-np.clip(z, -20, 20))))

    def as_dict(self) -> dict:
        return {
            "intercept": round(float(self.w[0]), 4),
            "w_ticket": round(float(self.w[1]), 4),
            "w_hour": round(float(self.w[2]), 4),
            "w_dow": round(float(self.w[3]), 4),
            "w_weekend": round(float(self.w[4]), 4),
            "threshold": round(float(self.threshold), 4),
            "features": [
                "ticket size / ₹500",
                "hour of day / 24",
                "day of week / 6",
                "weekend (0/1)",
            ],
            "note": "PEHLI_BAAR only fires when predicted 14-day return probability clears the threshold.",
        }


def cadence_from_prior(prior_ts: list[datetime], now: datetime, spend_90: float, spend_percentile: float) -> Cadence:
    n = len(prior_ts)
    if n == 0:
        return Cadence(0, 0.0, None, None, spend_90, spend_percentile)
    last = max(prior_ts)
    gap = (now - last).total_seconds() / 86400.0
    mean = std = None
    if n >= 4:
        ordered = sorted(prior_ts)
        gaps = np.diff([t.timestamp() for t in ordered]) / 86400.0
        mean = float(np.mean(gaps))
        std = float(np.std(gaps, ddof=1)) if len(gaps) > 1 else 0.6
        std = max(std, 0.45)
    return Cadence(n, gap, mean, std, spend_90, spend_percentile)


def decide_cue(cad: Cadence, propensity: Optional[float], threshold: float) -> Optional[Cue]:
    """At most one cue. Most payments return None — noise is the failure mode."""
    if cad.n_prior == 0:
        if propensity is None or propensity < threshold:
            return None
        return Cue(
            "PEHLI_BAAR",
            why_hi="इस दुकान पर पहले कोई भुगतान नहीं",
            why_en="no payment from this person before",
            propensity=propensity,
        )

    if cad.n_prior >= 4 and cad.mean is not None and cad.std is not None:
        bar = cad.mean + 2 * cad.std
        if cad.gap_days > bar:
            mean_r = max(1, int(round(cad.mean)))
            gap_r = int(round(cad.gap_days))
            if cad.gap_days >= 28:
                return Cue(
                    "LAUT_AAYE",
                    why_hi=f"{gap_r} दिन बाद लौटे — इनका रिदम हर {mean_r} दिन का था",
                    why_en=f"back after {gap_r} days; their rhythm was every {mean_r} days",
                )
            return Cue(
                "RUK_GAYE",
                why_hi=f"आमतौर पर हर {mean_r} दिन आते हैं, {gap_r} दिन हो गए",
                why_en=f"usually every {mean_r} days — {gap_r} days have passed",
            )

    if cad.spend_percentile >= 90:
        return Cue(
            "KHAAS_GRAHAK",
            why_hi="पिछले 90 दिन में सबसे ज़्यादा ख़र्च करने वाले 10% में",
            why_en="top 10% by spend at this shop in 90 days",
        )

    return None


def allow_cue(
    cue_type: str,
    bandit: dict[str, dict],
    shown_today: int,
    daily_cap: int,
    rng: np.random.Generator,
    epsilon: float = 0.12,
) -> bool:
    arm = bandit[cue_type]
    if arm["pruned"]:
        return False
    if shown_today >= daily_cap:
        return False
    live = {k: v for k, v in bandit.items() if not v["pruned"]}
    if rng.random() < epsilon:
        return True
    rates = {k: (v["rewards"] / v["pulls"] if v["pulls"] else 0.0) for k, v in live.items()}
    best = max(rates, key=rates.get)
    # Spend budget on types this merchant actually acts on.
    return rates[cue_type] >= max(0.12, rates[best] - 0.18)
