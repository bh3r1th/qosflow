from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {"arrival_rate_rps", "p95_latency"}


@dataclass(frozen=True)
class _FitResult:
    split_idx: int
    breakpoint_rps: float
    bic_piecewise: float
    bic_linear: float

    @property
    def bic_gain(self) -> float:
        return self.bic_linear - self.bic_piecewise


def _fit_line(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    slope, intercept = np.polyfit(x, y, 1)
    residuals = y - (slope * x + intercept)
    sse = float(np.sum(np.square(residuals)))
    return float(slope), float(intercept), sse


def _bic(rss: float, n_obs: int, n_params: int) -> float:
    # Guard against numerical issues when fit is nearly perfect.
    rss = max(rss, 1e-12)
    return float(n_obs * np.log(rss / n_obs) + n_params * np.log(n_obs))


def _resolve_quality_signal(df: pd.DataFrame) -> pd.Series:
    if "mean_quality" in df.columns:
        return pd.to_numeric(df["mean_quality"], errors="coerce")
    if "task_exact_match" in df.columns:
        return pd.to_numeric(df["task_exact_match"], errors="coerce")
    if "stability_edit_similarity" in df.columns:
        return pd.to_numeric(df["stability_edit_similarity"], errors="coerce")
    raise ValueError(
        "No quality signal found. Expected one of: mean_quality, task_exact_match, "
        "stability_edit_similarity"
    )


def _prepare_frame(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    out = df.copy()
    out["arrival_rate_rps"] = pd.to_numeric(out["arrival_rate_rps"], errors="coerce")
    out["quality_signal"] = _resolve_quality_signal(out)
    out = out.dropna(subset=["arrival_rate_rps", "quality_signal"]).sort_values("arrival_rate_rps")
    if len(out) < 5:
        raise ValueError("Need at least 5 valid points to evaluate a 1-breakpoint model")
    return out.reset_index(drop=True)


def _fit_best_breakpoint(df: pd.DataFrame, min_segment_size: int = 2) -> _FitResult:
    x = df["arrival_rate_rps"].to_numpy(dtype=float)
    y = df["quality_signal"].to_numpy(dtype=float)
    n = len(df)

    _, _, rss_linear = _fit_line(x, y)
    bic_linear = _bic(rss_linear, n_obs=n, n_params=2)

    start = min_segment_size
    end = n - min_segment_size
    if start >= end:
        raise ValueError("Not enough points for requested min_segment_size")

    best: _FitResult | None = None
    for split_idx in range(start, end):
        x_left, y_left = x[:split_idx], y[:split_idx]
        x_right, y_right = x[split_idx:], y[split_idx:]

        if len(np.unique(x_left)) < 2 or len(np.unique(x_right)) < 2:
            continue

        _, _, rss_left = _fit_line(x_left, y_left)
        _, _, rss_right = _fit_line(x_right, y_right)
        bic_piecewise = _bic(rss_left + rss_right, n_obs=n, n_params=4)

        breakpoint_rps = float((x[split_idx - 1] + x[split_idx]) / 2.0)
        candidate = _FitResult(
            split_idx=split_idx,
            breakpoint_rps=breakpoint_rps,
            bic_piecewise=bic_piecewise,
            bic_linear=bic_linear,
        )
        if best is None or candidate.bic_piecewise < best.bic_piecewise:
            best = candidate

    if best is None:
        raise RuntimeError("Unable to fit breakpoint model")
    return best


def detect_phase_transition(
    df: pd.DataFrame,
    *,
    bootstrap_samples: int = 200,
    min_segment_size: int = 2,
    random_state: int = 0,
) -> dict[str, float]:
    prepared = _prepare_frame(df)
    best = _fit_best_breakpoint(prepared, min_segment_size=min_segment_size)

    rng = np.random.default_rng(random_state)
    x = prepared["arrival_rate_rps"].to_numpy(dtype=float)
    boot_breakpoints: list[float] = []

    for _ in range(bootstrap_samples):
        sample_idx = rng.integers(0, len(prepared), len(prepared))
        sample_df = prepared.iloc[sample_idx].sort_values("arrival_rate_rps").reset_index(drop=True)
        # Resamples can collapse distinct x values; skip invalid trials.
        if sample_df["arrival_rate_rps"].nunique() < (min_segment_size * 2):
            continue
        try:
            boot_best = _fit_best_breakpoint(sample_df, min_segment_size=min_segment_size)
        except Exception:
            continue
        boot_breakpoints.append(boot_best.breakpoint_rps)

    if boot_breakpoints:
        ci_low, ci_high = np.percentile(np.array(boot_breakpoints), [2.5, 97.5]).tolist()
    else:
        ci_low = ci_high = best.breakpoint_rps

    return {
        "breakpoint_rps": float(best.breakpoint_rps),
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "bic_gain": float(best.bic_gain),
    }


def summarize_phase_input(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["arrival_rate_rps"] = pd.to_numeric(out.get("arrival_rate_rps"), errors="coerce")
    out["mean_quality"] = pd.to_numeric(_resolve_quality_signal(out), errors="coerce")

    if "var_quality" not in out.columns:
        out["var_quality"] = 0.0
    out["var_quality"] = pd.to_numeric(out["var_quality"], errors="coerce").fillna(0.0)

    if "p95_latency" not in out.columns:
        if "latency_ms_p95" in out.columns:
            out["p95_latency"] = pd.to_numeric(out["latency_ms_p95"], errors="coerce")
        else:
            out["p95_latency"] = np.nan

    return out[["arrival_rate_rps", "mean_quality", "var_quality", "p95_latency"]]


def detect_phase(input_df: pd.DataFrame | str) -> dict[str, float] | str:
    """Backward-compatible phase API.

    If passed a CSV path string, returns legacy labels (stable/degraded) based on p95 latency.
    If passed a DataFrame, returns piecewise phase transition statistics.
    """
    if isinstance(input_df, str):
        df = pd.read_csv(input_df)
        p95 = float(df["latency_ms_p95"].iloc[0]) if "latency_ms_p95" in df and not df.empty else 0.0
        return "stable" if p95 < 500 else "degraded"

    summary = summarize_phase_input(input_df)
    return detect_phase_transition(summary)


__all__ = ["detect_phase", "detect_phase_transition", "summarize_phase_input"]
