"""
Statistical machinery for the v2 eval (per ADR-0017 PR-5).

Replaces the 5-point composite regression rule with per-criterion bootstrap
CI gating. Reasoning:

- The old rule (Δcomposite ≥ 5 ⇒ regression) fires on n=3 ±20-point variance
  band noise. That's why the v1→v2 baseline diff (commit 92f7a2f) flagged
  "regressions" on three tasks that were likely just bimodal noise.
- The new rule: per-criterion paired bootstrap on Δp̂ with 10k resamples;
  regression flagged iff the 95% CI of Δp̂ is below 0 AND |Δp̂| ≥ 0.15
  (effect-size floor — small movements ignored regardless of significance).

No external deps; uses stdlib `random`, `math`, `statistics`.
"""

from __future__ import annotations
import math
import random
from typing import Iterable


def wilson_ci(passes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """
    Wilson score 95% CI on a Bernoulli pass rate.
    More accurate than normal-approximation at small n and near 0/1.

    >>> wilson_ci(0, 3)
    (0.0, 0.5614686887814769)
    >>> wilson_ci(3, 3)
    (0.4385313112185231, 1.0)
    """
    if n == 0:
        return (0.0, 1.0)
    p = passes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def paired_bootstrap_delta(
    baseline_runs: list[bool],
    candidate_runs: list[bool],
    iterations: int = 10_000,
    seed: int | None = 0,
) -> dict:
    """
    Paired bootstrap CI on Δp̂ = p̂_candidate - p̂_baseline.

    Pairs the i-th baseline run with the i-th candidate run (matched on
    fixture + run index), resamples pairs with replacement.

    If baseline_runs and candidate_runs have different lengths, the shorter
    one is truncated; you should already have re-run the candidate with
    the same n as baseline before calling this.

    Returns: {
      "delta": float,            # observed Δp̂
      "ci_low": float,           # 2.5%ile of resampled deltas
      "ci_high": float,          # 97.5%ile
      "n": int,                  # paired sample size
      "regressed": bool,         # ci_high < 0 AND |delta| >= effect_size_floor
      "effect_size_floor": float
    }
    """
    rng = random.Random(seed)
    n = min(len(baseline_runs), len(candidate_runs))
    if n == 0:
        return {
            "delta": 0.0, "ci_low": 0.0, "ci_high": 0.0,
            "n": 0, "regressed": False, "effect_size_floor": 0.15,
        }
    pairs = list(zip(baseline_runs[:n], candidate_runs[:n]))
    observed = (sum(c for _, c in pairs) - sum(b for b, _ in pairs)) / n

    deltas: list[float] = []
    for _ in range(iterations):
        idx = [rng.randrange(n) for _ in range(n)]
        bs = [pairs[i][0] for i in idx]
        cs = [pairs[i][1] for i in idx]
        deltas.append((sum(cs) - sum(bs)) / n)
    deltas.sort()
    ci_low = deltas[int(0.025 * iterations)]
    ci_high = deltas[int(0.975 * iterations) - 1]

    effect_size_floor = 0.15
    regressed = (ci_high < 0) and (abs(observed) >= effect_size_floor)
    return {
        "delta": round(observed, 4),
        "ci_low": round(ci_low, 4),
        "ci_high": round(ci_high, 4),
        "n": n,
        "regressed": regressed,
        "effect_size_floor": effect_size_floor,
    }


def variance_flag(runs: list[bool]) -> dict:
    """
    Flag fixtures whose per-criterion run-to-run variance suggests instability.
    Bernoulli SD = sqrt(p*(1-p)). At p=0.5 the SD is 0.5; we flag anything
    above SD=0.25 (i.e., p in roughly [0.25, 0.75]) as 'noisy — investigate
    before trusting deltas'. Per ADR-0017's noise-floor framing.
    """
    n = len(runs)
    if n == 0:
        return {"p": 0.0, "sd": 0.0, "noisy": False}
    passes = sum(1 for r in runs if r)
    p = passes / n
    sd = math.sqrt(p * (1 - p)) if 0 < p < 1 else 0.0
    return {"p": round(p, 4), "sd": round(sd, 4), "noisy": sd > 0.25, "n": n}


def aggregate_criterion(
    runs_per_fixture: dict[str, list[bool]]
) -> dict[str, dict]:
    """
    For each fixture, compute pass-rate + Wilson CI + variance flag.
    runs_per_fixture: {fixture_id: [bool, bool, ...]} where each bool is one
    run's pass/fail for ONE criterion.
    """
    out = {}
    for fid, runs in runs_per_fixture.items():
        passes = sum(1 for r in runs if r)
        ci_low, ci_high = wilson_ci(passes, len(runs))
        out[fid] = {
            "passes": passes,
            "n": len(runs),
            "rate": round(passes / len(runs), 4) if runs else 0.0,
            "ci_low": round(ci_low, 4),
            "ci_high": round(ci_high, 4),
            **variance_flag(runs),
        }
    return out
