from __future__ import annotations

import argparse
import asyncio
import random
import time

from qosflow.common.client import AsyncLLMClient
from qosflow.common.config import load_yaml


async def worker(client: AsyncLLMClient, duration_s: float, rate: float) -> None:
    end_at = time.monotonic() + duration_s
    while time.monotonic() < end_at:
        await asyncio.sleep(random.expovariate(rate))
        await client.generate("hello", params={"max_new_tokens": 16})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    cfg = load_yaml(args.config)

    async def run() -> None:
        client = AsyncLLMClient(
            base_url=str(cfg.get("target_url", "http://127.0.0.1:8000")),
            timeout=float(cfg.get("timeout_s", 30.0)),
        )
        await worker(
            client,
            float(cfg.get("duration_s", 10.0)),
            float(cfg.get("poisson_rate", 2.0)),
        )

    asyncio.run(run())


if __name__ == "__main__":
    main()
