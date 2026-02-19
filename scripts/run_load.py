from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime

from qosflow.common.config import QoSFlowConfig
from qosflow.common.repro import set_reproducible, write_manifest
from qosflow.loadgen.prompts import load_prompts
from qosflow.loadgen.runner import build_run_id, run_load


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run poisson async load generation against a server"
    )
    parser.add_argument("--config", required=True, help="Path to qosflow YAML config")
    args = parser.parse_args()

    config = QoSFlowConfig.from_yaml(args.config)
    set_reproducible(config.server.seed)

    run_ts = datetime.now(tz=UTC)
    run_id = build_run_id(run_ts, config.server, config.loadgen, config.experiment)
    run_dir = config.experiment.output_dir / "traces" / f"run_id={run_id}"
    write_manifest(path=run_dir / "manifest.json", config=config.model_dump(mode="json"))

    prompts = load_prompts(config.loadgen.prompt_source)
    summary = asyncio.run(
        run_load(
            config.server,
            config.loadgen,
            config.experiment,
            prompts,
            now=run_ts,
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
