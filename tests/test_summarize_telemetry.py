from __future__ import annotations

import json
from pathlib import Path

from scripts.summarize_telemetry import summarize_telemetry


def test_summarize_telemetry_outputs_expected_stats(tmp_path: Path) -> None:
    telemetry = tmp_path / "telemetry.csv"
    output = tmp_path / "summary.json"
    telemetry.write_text(
        "timestamp,gpu_util,mem_used_mb,mem_total_mb,power_w,temp_c\n"
        "2025-01-01T00:00:00+00:00,20,1000,2000,100,70\n"
        "2025-01-01T00:00:01+00:00,40,1200,2000,110,71\n",
        encoding="utf-8",
    )

    summary = summarize_telemetry(telemetry, output)

    assert summary["samples"] == 2
    assert summary["mean_gpu_util"] == 30.0
    assert summary["max_gpu_util"] == 40.0
    assert summary["mean_mem_used_mb"] == 1100.0
    assert summary["max_mem_used_mb"] == 1200.0
    assert json.loads(output.read_text(encoding="utf-8"))["max_gpu_util"] == 40.0
