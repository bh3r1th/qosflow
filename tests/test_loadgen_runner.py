from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from qosflow.common.config import ExperimentConfig, LoadGenConfig, LoadMixConfig, ServerConfig
from qosflow.common.io import read_jsonl
from qosflow.common.schema import PromptRecord
from qosflow.loadgen.runner import build_run_id, run_load


class _DeterministicRng:
    def expovariate(self, _rate: float) -> float:
        return 0.001

    def choices(self, population, weights=None, k=1):  # noqa: ANN001, ANN201
        return [population[0]] * k

    def choice(self, population):  # noqa: ANN001, ANN201
        return population[0]


class _FakeClient:
    async def generate(self, prompt: str, params=None):  # noqa: ANN001, ANN201
        return f"ok:{prompt}", {"prefill_ms": 1.0, "decode_ms": 2.0}, 200

    async def aclose(self) -> None:
        return None


def _server_config() -> ServerConfig:
    return ServerConfig(
        host="127.0.0.1",
        port=8000,
        model="test-model",
        dtype="float16",
        max_new_tokens=12,
        temperature=0.1,
        top_p=0.9,
        seed=42,
        max_num_seqs=8,
        max_num_batched_tokens=1024,
        scheduler_delay_ms=0,
    )


def test_build_run_id_is_deterministic() -> None:
    timestamp = datetime(2025, 1, 2, 3, 4, 5, tzinfo=UTC)
    loadgen = LoadGenConfig(
        arrival_rate_rps=5.0,
        concurrency=2,
        duration_s=1,
        warmup_s=0,
        repeats=2,
        prompt_source=Path("prompts.jsonl"),
        mix=LoadMixConfig(short=1.0, med=0.0, long=0.0),
    )
    experiment = ExperimentConfig(name="exp", output_dir=Path("out"))

    run_id_1 = build_run_id(timestamp, _server_config(), loadgen, experiment)
    run_id_2 = build_run_id(timestamp, _server_config(), loadgen, experiment)

    assert run_id_1 == run_id_2


def test_run_load_respects_warmup_and_repeats(tmp_path: Path) -> None:
    loadgen = LoadGenConfig(
        arrival_rate_rps=100.0,
        concurrency=2,
        duration_s=1,
        warmup_s=0,
        repeats=3,
        prompt_source=tmp_path / "prompts.jsonl",
        mix=LoadMixConfig(short=1.0, med=0.0, long=0.0),
    )
    experiment = ExperimentConfig(name="exp", output_dir=tmp_path)
    prompts = [PromptRecord(prompt_id="p-short", text="tiny", length_bucket="short")]

    summary = asyncio.run(
        run_load(
            _server_config(),
            loadgen,
            experiment,
            prompts,
            now=datetime(2025, 1, 2, 3, 4, 5, tzinfo=UTC),
            rng=_DeterministicRng(),
            client_factory=lambda: _FakeClient(),
        )
    )

    rows = read_jsonl(summary.trace_path)

    assert summary.sent > 0
    assert summary.sent == summary.success
    assert summary.failed == 0
    assert len(rows) == summary.sent
    assert {row["repeat_idx"] for row in rows}.issubset({0, 1, 2})
