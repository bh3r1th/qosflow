from __future__ import annotations

import json
from pathlib import Path

from qosflow.metrics.latency import compute_latency_metrics
from qosflow.metrics.stability import compute_stability_metrics
from qosflow.metrics.task import compute_task_metrics
from scripts.run_eval import run_eval


def test_latency_metrics() -> None:
    import pandas as pd

    df = pd.DataFrame(
        [
            {"total_ms": 10.0, "ts_start_ns": 0, "ts_end_ns": 10_000_000, "system.error": None},
            {
                "total_ms": 20.0,
                "ts_start_ns": 10_000_000,
                "ts_end_ns": 20_000_000,
                "system.error": "boom",
            },
            {
                "total_ms": 30.0,
                "ts_start_ns": 20_000_000,
                "ts_end_ns": 30_000_000,
                "system.error": None,
            },
        ]
    )

    metrics, _ = compute_latency_metrics(df)
    assert metrics["latency_ms_p50"] == 20.0
    assert metrics["latency_ms_p95"] == 29.0
    assert metrics["latency_ms_p99"] == 29.8
    assert metrics["error_rate"] == 1 / 3
    assert metrics["throughput_rps"] == 100.0


def test_task_metrics() -> None:
    import pandas as pd

    df = pd.DataFrame(
        [
            {"prompt_id": "p1", "repeat_idx": 0, "expected": "a b", "output_text": "a b"},
            {"prompt_id": "p2", "repeat_idx": 0, "expected": "a b", "output_text": "a c"},
        ]
    )
    metrics, per_row = compute_task_metrics(df)

    assert metrics["task_count"] == 2
    assert metrics["task_exact_match"] == 0.5
    assert metrics["task_token_f1"] == 0.75
    assert list(per_row.columns) == ["prompt_id", "repeat_idx", "exact_match", "token_f1"]


def test_stability_metrics() -> None:
    import pandas as pd

    df = pd.DataFrame(
        [
            {"prompt_id": "p1", "output_text": "hello"},
            {"prompt_id": "p1", "output_text": "hello"},
            {"prompt_id": "p1", "output_text": "hullo"},
            {"prompt_id": "p2", "output_text": "world"},
            {"prompt_id": "p2", "output_text": "world"},
        ]
    )
    metrics, per_prompt = compute_stability_metrics(df)

    assert metrics["stability_prompt_groups"] == 2
    assert len(per_prompt) == 2
    p1_rate = float(per_prompt.loc[per_prompt["prompt_id"] == "p1", "exact_match_rate"].iloc[0])
    assert p1_rate == 2 / 3


def test_run_eval_writes_outputs(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.jsonl"
    trace_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "prompt_id": "p1",
                        "repeat_idx": 0,
                        "ts_start_ns": 0,
                        "ts_end_ns": 1_000_000,
                        "total_ms": 1.0,
                        "output_text": "alpha beta",
                        "expected": "alpha beta",
                        "system": {"error": None},
                    }
                ),
                json.dumps(
                    {
                        "prompt_id": "p1",
                        "repeat_idx": 1,
                        "ts_start_ns": 1_000_000,
                        "ts_end_ns": 2_000_000,
                        "total_ms": 1.0,
                        "output_text": "alpha",
                        "expected": "alpha beta",
                        "system": {"error": None},
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    metrics, df = run_eval(str(tmp_path / "*.jsonl"), str(tmp_path))
    assert metrics["trace_files"] == 1
    assert metrics["trace_rows"] == 2
    assert "task_exact_match" in metrics
    assert not df.empty

    out_dir = tmp_path / "eval"
    assert (out_dir / "metrics.json").exists()
    assert (out_dir / "metrics.csv").exists()
