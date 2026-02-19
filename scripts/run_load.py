from __future__ import annotations

import argparse
import asyncio

from qosflow.common.config import QoSFlowConfig
from qosflow.loadgen.prompts import load_prompts
from qosflow.loadgen.runner import run_load


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run poisson async load generation against a server"
    )
    parser.add_argument("--config", required=True, help="Path to qosflow YAML config")
    args = parser.parse_args()

    config = QoSFlowConfig.from_yaml(args.config)
    prompts = load_prompts(config.loadgen.prompt_source)
    summary = asyncio.run(
        run_load(
            config.server,
            config.loadgen,
            config.experiment,
            prompts,
        )
    )

    print(f"run_id={summary.run_id}")
    print(f"trace_path={summary.trace_path}")
    print(
        "summary "
        f"sent={summary.sent} success={summary.success} failed={summary.failed} "
        f"p50_total_ms={summary.p50_total_ms:.2f} p95_total_ms={summary.p95_total_ms:.2f}"
    )


if __name__ == "__main__":
    main()
