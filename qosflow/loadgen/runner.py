from __future__ import annotations

import asyncio
import json
import random
import time
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from qosflow.common.client import AsyncLLMClient
from qosflow.common.config import ExperimentConfig, LoadGenConfig, ServerConfig
from qosflow.common.hashing import sha256_normalized_json, sha256_normalized_text
from qosflow.common.io import ensure_dir
from qosflow.common.schema import (
    PromptRecord,
    TraceParams,
    TraceRecord,
    TraceServerSnapshot,
    TraceSystem,
)
from qosflow.loadgen.mix import PromptMixSampler


@dataclass(frozen=True)
class LoadGenSummary:
    run_id: str
    trace_path: Path
    sent: int
    success: int
    failed: int
    p50_total_ms: float
    p95_total_ms: float


def build_run_id(
    timestamp: datetime,
    server_config: ServerConfig,
    loadgen_config: LoadGenConfig,
    experiment_config: ExperimentConfig,
) -> str:
    timestamp_token = timestamp.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    hash_input = {
        "server": server_config.model_dump(mode="json"),
        "loadgen": loadgen_config.model_dump(mode="json"),
        "experiment": experiment_config.model_dump(mode="json"),
    }
    config_hash = sha256_normalized_json(hash_input)[:12]
    return f"{timestamp_token}-{config_hash}"


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    idx = int(round((len(sorted_values) - 1) * pct))
    idx = max(0, min(idx, len(sorted_values) - 1))
    return sorted_values[idx]


async def run_load(
    server_config: ServerConfig,
    loadgen_config: LoadGenConfig,
    experiment_config: ExperimentConfig,
    prompts: Sequence[PromptRecord],
    *,
    now: datetime | None = None,
    rng: random.Random | None = None,
    client_factory: Callable[[], AsyncLLMClient] | None = None,
) -> LoadGenSummary:
    if not prompts:
        raise ValueError("prompts list must not be empty")
    if loadgen_config.arrival_rate_rps <= 0:
        raise ValueError("arrival_rate_rps must be > 0")
    if loadgen_config.repeats <= 0:
        raise ValueError("repeats must be > 0")

    run_ts = now or datetime.now(tz=UTC)
    run_id = build_run_id(run_ts, server_config, loadgen_config, experiment_config)
    trace_path = (
        ensure_dir(experiment_config.output_dir)
        / "traces"
        / f"run_id={run_id}"
        / "trace.jsonl"
    )
    ensure_dir(trace_path.parent)

    schedule_rng = rng or random.Random()
    sampler = PromptMixSampler(
        prompts,
        {
            "short": loadgen_config.mix.short,
            "med": loadgen_config.mix.med,
            "long": loadgen_config.mix.long,
        },
        rng=schedule_rng,
    )
    pending_repeats: deque[tuple[PromptRecord, int]] = deque()

    concurrency = max(1, loadgen_config.concurrency)
    semaphore = asyncio.Semaphore(concurrency)

    base_url = f"http://{server_config.host}:{server_config.port}"
    if client_factory is None:
        client = AsyncLLMClient(base_url=base_url, timeout=60.0)
    else:
        client = client_factory()

    params = TraceParams(
        temperature=server_config.temperature,
        top_p=server_config.top_p,
        seed=server_config.seed,
        max_new_tokens=server_config.max_new_tokens,
    )
    server_snapshot = TraceServerSnapshot(
        model=server_config.model,
        dtype=server_config.dtype,
        batching_knobs={
            "max_num_seqs": server_config.max_num_seqs,
            "max_num_batched_tokens": server_config.max_num_batched_tokens,
            "scheduler_delay_ms": server_config.scheduler_delay_ms,
        },
    )

    stats = {"sent": 0, "success": 0, "failed": 0}
    latencies_ms: list[float] = []
    write_lock = asyncio.Lock()

    warmup_end = time.monotonic() + float(loadgen_config.warmup_s)
    stop_at = warmup_end + float(loadgen_config.duration_s)

    async def fire_request(prompt: PromptRecord, repeat_idx: int, should_record: bool) -> None:
        async with semaphore:
            ts_start_ns = time.time_ns()
            output_text = ""
            status_code = 0
            err_msg: str | None = None
            batch_size: int | None = None
            queue_ms: float | None = None
            prefill_ms: float | None = None
            decode_ms: float | None = None

            try:
                output_text, timings, status_code = await client.generate(
                    prompt.text,
                    params=params.model_dump(mode="json"),
                )
                batch_size = timings.get("batch_size")
                queue_ms = timings.get("queue_ms")
                prefill_ms = timings.get("prefill_ms")
                decode_ms = timings.get("decode_ms")
            except Exception as exc:  # noqa: BLE001
                err_msg = str(exc)
            ts_end_ns = time.time_ns()
            total_ms = (ts_end_ns - ts_start_ns) / 1_000_000.0

            if not should_record:
                return

            stats["sent"] += 1
            if err_msg is None:
                stats["success"] += 1
            else:
                stats["failed"] += 1
            latencies_ms.append(total_ms)

            trace = TraceRecord(
                request_id=str(uuid4()),
                run_id=run_id,
                prompt_id=prompt.prompt_id,
                repeat_idx=repeat_idx,
                ts_start_ns=ts_start_ns,
                ts_end_ns=ts_end_ns,
                total_ms=total_ms,
                params=params,
                server=server_snapshot,
                system=TraceSystem(
                    http_status=status_code,
                    error=err_msg,
                    batch_size=batch_size,
                    queue_ms=queue_ms,
                    prefill_ms=prefill_ms,
                    decode_ms=decode_ms,
                ),
                prompt_hash=sha256_normalized_text(prompt.text),
                output_hash=sha256_normalized_text(output_text),
                prompt_len_chars=len(prompt.text),
                output_len_chars=len(output_text),
                output_text=output_text,
            )

            async with write_lock:
                with trace_path.open("a", encoding="utf-8") as handle:
                    payload = json.dumps(trace.model_dump(mode="json"), ensure_ascii=False)
                    handle.write(payload + "\n")

    tasks: list[asyncio.Task[None]] = []

    try:
        while True:
            now_monotonic = time.monotonic()
            if now_monotonic >= stop_at:
                break

            wait_s = schedule_rng.expovariate(loadgen_config.arrival_rate_rps)
            await asyncio.sleep(wait_s)
            now_monotonic = time.monotonic()
            if now_monotonic >= stop_at:
                break

            if not pending_repeats:
                chosen = sampler.sample()
                for repeat_idx in range(loadgen_config.repeats):
                    pending_repeats.append((chosen, repeat_idx))

            prompt, repeat_idx = pending_repeats.popleft()
            should_record = now_monotonic >= warmup_end
            tasks.append(asyncio.create_task(fire_request(prompt, repeat_idx, should_record)))

        if tasks:
            await asyncio.gather(*tasks)
    finally:
        await client.aclose()

    return LoadGenSummary(
        run_id=run_id,
        trace_path=trace_path,
        sent=stats["sent"],
        success=stats["success"],
        failed=stats["failed"],
        p50_total_ms=_percentile(latencies_ms, 0.50),
        p95_total_ms=_percentile(latencies_ms, 0.95),
    )


__all__ = ["LoadGenSummary", "build_run_id", "run_load"]
