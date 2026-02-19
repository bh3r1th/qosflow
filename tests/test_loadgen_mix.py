from __future__ import annotations

import random

import pytest

from qosflow.common.schema import PromptRecord
from qosflow.loadgen.mix import PromptMixSampler


def _prompt(prompt_id: str, bucket: str) -> PromptRecord:
    return PromptRecord(prompt_id=prompt_id, text=prompt_id, length_bucket=bucket)


def test_prompt_mix_sampler_draws_from_weighted_buckets() -> None:
    prompts = [_prompt("s1", "short"), _prompt("m1", "med"), _prompt("l1", "long")]
    sampler = PromptMixSampler(
        prompts,
        {"short": 1.0, "med": 0.0, "long": 0.0},
        rng=random.Random(7),
    )

    sampled = sampler.sample_many(10)

    assert {item.length_bucket for item in sampled} == {"short"}


def test_prompt_mix_sampler_errors_when_no_weighted_non_empty_buckets() -> None:
    prompts = [_prompt("s1", "short")]
    with pytest.raises(ValueError, match="No non-empty prompt buckets with positive weight"):
        PromptMixSampler(
            prompts,
            {"short": 0.0, "med": 1.0, "long": 2.0},
            rng=random.Random(0),
        )


def test_prompt_mix_sampler_errors_on_missing_bucket() -> None:
    prompt = PromptRecord(prompt_id="p1", text="hello")
    with pytest.raises(ValueError, match="missing length_bucket"):
        PromptMixSampler([prompt], {"short": 1.0, "med": 1.0, "long": 1.0})
