from __future__ import annotations

import argparse
import json
from glob import glob
from pathlib import Path
from typing import Any

import pandas as pd

from qosflow.common.io import ensure_dir, read_jsonl
from qosflow.metrics.latency import compute_latency_metrics
from qosflow.metrics.stability import compute_stability_metrics
from qosflow.metrics.task import compute_task_metrics


def _load_traces(path_glob: str) -> pd.DataFrame:
    paths = sorted(glob(path_glob))
    rows: list[dict[str, Any]] = []
    for path in paths:
        for row in read_jsonl(path):
            rows.append(row)
    if not rows:
        return pd.DataFrame()
    return pd.json_normalize(rows)


def run_eval(traces_glob: str, output_dir: str | Path) -> tuple[dict[str, Any], pd.DataFrame]:
    df = _load_traces(traces_glob)

    all_metrics: dict[str, Any] = {
        "trace_files": len(glob(traces_glob)),
        "trace_rows": int(len(df)),
    }
    table_parts: list[pd.DataFrame] = []

    latency_metrics, latency_df = compute_latency_metrics(df)
    all_metrics.update(latency_metrics)
    if not latency_df.empty:
        table_parts.append(latency_df)

    task_metrics, task_df = compute_task_metrics(df)
    all_metrics.update(task_metrics)
    if not task_df.empty:
        task_summary = (
            task_df[["exact_match", "token_f1"]]
            .mean()
            .to_frame()
            .T.rename(columns={"exact_match": "task_exact_match", "token_f1": "task_token_f1"})
        )
        table_parts.append(task_summary)

    stability_metrics, stability_df = compute_stability_metrics(df)
    all_metrics.update(stability_metrics)
    if not stability_df.empty:
        stability_summary = (
            stability_df[["exact_match_rate", "edit_similarity"]]
            .mean()
            .to_frame()
            .T.rename(
                columns={
                    "exact_match_rate": "stability_exact_match_rate",
                    "edit_similarity": "stability_edit_similarity",
                }
            )
        )
        table_parts.append(stability_summary)

    output_eval_dir = ensure_dir(Path(output_dir) / "eval")
    metrics_json_path = output_eval_dir / "metrics.json"
    metrics_csv_path = output_eval_dir / "metrics.csv"

    merged_df = pd.concat(table_parts, axis=1) if table_parts else pd.DataFrame([all_metrics])
    for key, value in all_metrics.items():
        if key not in merged_df.columns:
            merged_df[key] = value

    with metrics_json_path.open("w", encoding="utf-8") as f:
        json.dump(all_metrics, f, indent=2, ensure_ascii=False)

    merged_df.to_csv(metrics_csv_path, index=False)
    return all_metrics, merged_df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--traces", required=True, help="Glob for trace JSONL files")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    metrics, _ = run_eval(traces_glob=args.traces, output_dir=args.output_dir)
    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
