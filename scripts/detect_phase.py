from __future__ import annotations

import argparse
import json
import re
from glob import glob
from pathlib import Path
from typing import Any

import pandas as pd

from qosflow.analysis.phase import detect_phase_transition, summarize_phase_input
from qosflow.common.io import ensure_dir


def _extract_rate_from_path(path: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*rps", path)
    return float(match.group(1)) if match else None


def _load_metrics_file(path: str) -> dict[str, Any]:
    p = Path(path)
    if p.suffix.lower() == ".json":
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    if p.suffix.lower() == ".csv":
        frame = pd.read_csv(p)
        if frame.empty:
            return {}
        return frame.iloc[0].to_dict()
    raise ValueError(f"Unsupported metrics file: {path}")


def _to_phase_row(metrics: dict[str, Any], source_path: str) -> dict[str, Any]:
    row = dict(metrics)
    if "arrival_rate_rps" not in row:
        row["arrival_rate_rps"] = row.get("throughput_rps")
    if row.get("arrival_rate_rps") is None:
        row["arrival_rate_rps"] = _extract_rate_from_path(source_path)
    if "p95_latency" not in row and "latency_ms_p95" in row:
        row["p95_latency"] = row["latency_ms_p95"]
    return row


def run_detect_phase(input_glob: str, output_dir: str | Path, bootstrap_samples: int = 200) -> dict[str, float]:
    metric_paths = sorted(glob(input_glob))
    if not metric_paths:
        raise ValueError(f"No files matched: {input_glob}")

    rows = [_to_phase_row(_load_metrics_file(path), path) for path in metric_paths]
    raw_df = pd.DataFrame(rows)
    summary_df = summarize_phase_input(raw_df).dropna(subset=["arrival_rate_rps", "p95_latency"])

    result = detect_phase_transition(summary_df, bootstrap_samples=bootstrap_samples)

    out_dir = ensure_dir(output_dir)
    phase_json = Path(out_dir) / "phase.json"
    summary_csv = Path(out_dir) / "phase_summary.csv"

    with phase_json.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    summary_df.sort_values("arrival_rate_rps").to_csv(summary_csv, index=False)

    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-glob", required=True, help="Glob for per-load eval metric files (.json/.csv)")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=200)
    args = parser.parse_args()

    result = run_detect_phase(
        input_glob=args.input_glob,
        output_dir=args.output_dir,
        bootstrap_samples=args.bootstrap_samples,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
