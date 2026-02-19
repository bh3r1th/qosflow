from __future__ import annotations

import random

import pandas as pd
import pytest
from pydantic import ValidationError

from qosflow.common.config import QoSFlowConfig
from qosflow.common.schema import TraceRecord
from qosflow.metrics.stability import compute_stability_metrics


def test_config_loading_rejects_unknown_keys(tmp_path) -> None:
    cfg_path = tmp_path / "bad_config.yaml"
    cfg_path.write_text(
        """
server:
  host: 127.0.0.1
  port: 8000
  model: test-model
  dtype: float16
  max_new_tokens: 32
  temperature: 0.1
  top_p: 0.9
  seed: 123
  max_num_seqs: 4
  max_num_batched_tokens: 2048
  scheduler_delay_ms: 0
  unknown_field: should_fail
loadgen:
  arrival_rate_rps: 2.0
  concurrency: 1
  duration_s: 1
  warmup_s: 0
  repeats: 1
  prompt_source: prompts.jsonl
  mix:
    short: 1.0
    med: 0.0
    long: 0.0
eval:
  enable_embeddings: false
  embedding_model: none
experiment:
  name: demo
  output_dir: out
""",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        QoSFlowConfig.from_yaml(cfg_path)


def test_trace_schema_round_trip_validation() -> None:
    record = TraceRecord.model_validate(
        {
            "request_id": "req-1",
            "run_id": "run-1",
            "prompt_id": "p1",
            "repeat_idx": 0,
            "ts_start_ns": 10,
            "ts_end_ns": 110,
            "total_ms": 0.1,
            "params": {
                "temperature": 0.2,
                "top_p": 0.95,
                "seed": 7,
                "max_new_tokens": 16,
            },
            "server": {
                "model": "demo-model",
                "dtype": "float16",
                "batching_knobs": {"max_num_seqs": 4},
            },
            "system": {
                "http_status": 200,
                "batch_size": 1,
                "queue_ms": 0.0,
                "prefill_ms": 1.0,
                "decode_ms": 2.0,
            },
            "prompt_hash": "abc",
            "output_hash": "def",
            "prompt_len_chars": 5,
            "output_len_chars": 2,
            "output_text": "ok",
        }
    )

    encoded = record.model_dump_json()
    decoded = TraceRecord.model_validate_json(encoded)

    assert decoded == record


def test_poisson_sampler_mean_interarrival_is_reasonable() -> None:
    rate = 12.5
    expected_mean = 1.0 / rate
    rng = random.Random(2025)
    samples = [rng.expovariate(rate) for _ in range(2000)]
    observed_mean = sum(samples) / len(samples)

    assert observed_mean == pytest.approx(expected_mean, rel=0.06)


def test_stability_metric_correctness_small_synthetic() -> None:
    df = pd.DataFrame(
        [
            {"prompt_id": "p1", "output_text": "aa"},
            {"prompt_id": "p1", "output_text": "aa"},
            {"prompt_id": "p1", "output_text": "ab"},
            {"prompt_id": "p2", "output_text": "x"},
            {"prompt_id": "p2", "output_text": "y"},
        ]
    )

    metrics, per_prompt = compute_stability_metrics(df)

    assert metrics["stability_prompt_groups"] == 2
    assert metrics["stability_exact_match_rate"] == pytest.approx((2 / 3 + 1 / 2) / 2)
    assert metrics["stability_edit_similarity"] == pytest.approx((2 / 3 + 0.0) / 2)

    p1 = per_prompt.loc[per_prompt["prompt_id"] == "p1"].iloc[0]
    p2 = per_prompt.loc[per_prompt["prompt_id"] == "p2"].iloc[0]
    assert float(p1["exact_match_rate"]) == pytest.approx(2 / 3)
    assert float(p1["edit_similarity"]) == pytest.approx(2 / 3)
    assert float(p2["exact_match_rate"]) == pytest.approx(1 / 2)
    assert float(p2["edit_similarity"]) == pytest.approx(0.0)
