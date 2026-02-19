from __future__ import annotations

import json

import pandas as pd

from qosflow.analysis.phase import detect_phase_transition
from scripts.detect_phase import run_detect_phase


def test_detect_phase_transition_piecewise_breakpoint() -> None:
    df = pd.DataFrame(
        {
            "arrival_rate_rps": [10, 20, 30, 40, 50, 60, 70, 80],
            "mean_quality": [0.99, 0.98, 0.97, 0.96, 0.85, 0.72, 0.6, 0.45],
            "var_quality": [0.0] * 8,
            "p95_latency": [110, 120, 130, 140, 180, 230, 290, 340],
        }
    )

    result = detect_phase_transition(df, bootstrap_samples=50, random_state=7)
    assert 35.0 <= result["breakpoint_rps"] <= 55.0
    assert result["ci_low"] <= result["breakpoint_rps"] <= result["ci_high"]
    assert result["bic_gain"] > 0


def test_run_detect_phase_writes_outputs(tmp_path) -> None:
    loads = [10, 20, 30, 40, 50, 60]
    qualities = [0.98, 0.97, 0.96, 0.8, 0.7, 0.58]

    for load, quality in zip(loads, qualities):
        out = tmp_path / f"{load}rps"
        out.mkdir()
        payload = {
            "arrival_rate_rps": load,
            "task_exact_match": quality,
            "latency_ms_p95": 100 + load,
            "var_quality": 0.01,
        }
        (out / "metrics.json").write_text(json.dumps(payload), encoding="utf-8")

    result = run_detect_phase(str(tmp_path / "*" / "metrics.json"), tmp_path / "phase", bootstrap_samples=30)

    assert "breakpoint_rps" in result
    assert (tmp_path / "phase" / "phase.json").exists()
    summary = pd.read_csv(tmp_path / "phase" / "phase_summary.csv")
    assert list(summary.columns) == ["arrival_rate_rps", "mean_quality", "var_quality", "p95_latency"]
    assert len(summary) == len(loads)
