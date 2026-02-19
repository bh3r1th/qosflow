from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import fmean


def _collect_numeric(rows: list[dict[str, str]], key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        raw = (row.get(key) or "").strip()
        if not raw:
            continue
        try:
            values.append(float(raw))
        except ValueError:
            continue
    return values


def summarize_telemetry(
    input_csv: str | Path, output_json: str | Path
) -> dict[str, float | int | None]:
    in_path = Path(input_csv)
    with in_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    gpu_util = _collect_numeric(rows, "gpu_util")
    mem_used = _collect_numeric(rows, "mem_used_mb")

    summary: dict[str, float | int | None] = {
        "samples": len(rows),
        "mean_gpu_util": fmean(gpu_util) if gpu_util else None,
        "max_gpu_util": max(gpu_util) if gpu_util else None,
        "mean_mem_used_mb": fmean(mem_used) if mem_used else None,
        "max_mem_used_mb": max(mem_used) if mem_used else None,
    }

    out_path = Path(output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)

    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to telemetry.csv")
    parser.add_argument("--output", required=True, help="Path to summary.json")
    args = parser.parse_args()

    summary = summarize_telemetry(args.input, args.output)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
