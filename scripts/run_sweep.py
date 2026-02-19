from __future__ import annotations

import argparse
from pathlib import Path

from qosflow.analysis.sweep import run_sweep


def _parse_rates(raw_values: list[str]) -> list[float]:
    rates: list[float] = []
    for raw in raw_values:
        parts = [part.strip() for part in raw.split(",")]
        rates.extend(float(part) for part in parts if part)
    return rates


def main() -> None:
    parser = argparse.ArgumentParser(description="Run multi-load sweep and aggregate eval metrics")
    parser.add_argument("--config", required=True, help="Path to qosflow YAML config")
    parser.add_argument(
        "--arrival-rates",
        nargs="+",
        required=True,
        help="Arrival rates in req/s (supports repeated values or comma-separated lists)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Sweep output directory (defaults to experiment.output_dir in config)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Do not skip lambdas that already have eval/metrics.json",
    )
    args = parser.parse_args()

    arrival_rates = _parse_rates(args.arrival_rates)
    summary_df = run_sweep(
        config_path=args.config,
        arrival_rates=arrival_rates,
        output_dir=Path(args.output_dir) if args.output_dir else None,
        resume=not args.no_resume,
    )

    summary_path = (Path(args.output_dir) if args.output_dir else None)
    if summary_path is None:
        from qosflow.common.config import QoSFlowConfig

        summary_path = QoSFlowConfig.from_yaml(args.config).experiment.output_dir
    print(f"summary_path={summary_path / 'summary.csv'}")
    print(f"rows={len(summary_df)}")


if __name__ == "__main__":
    main()
