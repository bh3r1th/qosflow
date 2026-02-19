from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from qosflow.common.config import QoSFlowConfig
from qosflow.common.io import ensure_dir
from qosflow.loadgen.prompts import load_prompts
from qosflow.loadgen.runner import run_load
from scripts.run_eval import run_eval


def _lambda_token(arrival_rate_rps: float) -> str:
    return format(float(arrival_rate_rps), "g")


def _metrics_with_arrival(metrics: dict[str, Any], arrival_rate_rps: float) -> dict[str, Any]:
    row = dict(metrics)
    row["arrival_rate_rps"] = float(arrival_rate_rps)
    if "p95_latency" not in row and "latency_ms_p95" in row:
        row["p95_latency"] = row["latency_ms_p95"]
    return row


def run_sweep(
    *,
    config_path: str | Path,
    arrival_rates: Iterable[float],
    output_dir: str | Path | None = None,
    resume: bool = True,
) -> pd.DataFrame:
    base_cfg = QoSFlowConfig.from_yaml(config_path)
    rates = [float(rate) for rate in arrival_rates]
    if not rates:
        raise ValueError("arrival_rates must not be empty")

    sweep_output_dir = ensure_dir(output_dir or base_cfg.experiment.output_dir)
    prompts = load_prompts(base_cfg.loadgen.prompt_source)

    all_rows: list[dict[str, Any]] = []

    for arrival_rate in rates:
        token = _lambda_token(arrival_rate)
        lambda_dir = ensure_dir(sweep_output_dir / f"lambda={token}")
        metrics_path = lambda_dir / "eval" / "metrics.json"

        if resume and metrics_path.exists():
            with metrics_path.open("r", encoding="utf-8") as f:
                metrics = dict(json.load(f))
        else:
            loadgen_cfg = base_cfg.loadgen.model_copy(update={"arrival_rate_rps": arrival_rate})
            experiment_cfg = base_cfg.experiment.model_copy(
                update={
                    "name": f"{base_cfg.experiment.name}-lambda={token}",
                    "output_dir": lambda_dir,
                }
            )

            asyncio.run(
                run_load(
                    base_cfg.server,
                    loadgen_cfg,
                    experiment_cfg,
                    prompts,
                )
            )

            traces_glob = str(lambda_dir / "traces" / "run_id=*" / "trace.jsonl")
            metrics, _ = run_eval(traces_glob=traces_glob, output_dir=lambda_dir)

        all_rows.append(_metrics_with_arrival(metrics, arrival_rate))

    summary_df = pd.DataFrame(all_rows).sort_values("arrival_rate_rps").reset_index(drop=True)
    summary_path = sweep_output_dir / "summary.csv"
    summary_df.to_csv(summary_path, index=False)
    return summary_df


__all__ = ["run_sweep"]
