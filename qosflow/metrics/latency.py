from __future__ import annotations

from typing import Any

import pandas as pd


def compute_latency_metrics(df: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    if df.empty:
        empty = {
            "count": 0,
            "latency_ms_p50": 0.0,
            "latency_ms_p95": 0.0,
            "latency_ms_p99": 0.0,
            "error_rate": 0.0,
            "throughput_rps": 0.0,
        }
        return empty, pd.DataFrame([empty])

    latency_col = "total_ms" if "total_ms" in df.columns else "latency_ms"
    latencies = pd.to_numeric(df.get(latency_col, pd.Series(dtype=float)), errors="coerce")
    latencies = latencies.dropna()

    if "system.error" in df.columns:
        failed = df["system.error"].notna().sum()
    elif "error" in df.columns:
        failed = df["error"].notna().sum()
    else:
        failed = 0

    count = int(len(df))
    duration_seconds = 0.0
    if "ts_start_ns" in df.columns and "ts_end_ns" in df.columns and not df.empty:
        start_ns = pd.to_numeric(df["ts_start_ns"], errors="coerce").dropna()
        end_ns = pd.to_numeric(df["ts_end_ns"], errors="coerce").dropna()
        if not start_ns.empty and not end_ns.empty:
            duration_seconds = max((end_ns.max() - start_ns.min()) / 1_000_000_000.0, 0.0)

    throughput = count / duration_seconds if duration_seconds > 0 else 0.0

    metrics = {
        "count": count,
        "latency_ms_p50": float(latencies.quantile(0.5)) if not latencies.empty else 0.0,
        "latency_ms_p95": float(latencies.quantile(0.95)) if not latencies.empty else 0.0,
        "latency_ms_p99": float(latencies.quantile(0.99)) if not latencies.empty else 0.0,
        "error_rate": float(failed / count) if count else 0.0,
        "throughput_rps": float(throughput),
    }
    return metrics, pd.DataFrame([metrics])


__all__ = ["compute_latency_metrics"]
