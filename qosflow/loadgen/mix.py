from __future__ import annotations

import random
from typing import Iterable

from qosflow.common.schema import PromptRecord
from qosflow.loadgen.prompts import LengthBucket


class PromptMixSampler:
    def __init__(
        self,
        prompts: Iterable[PromptRecord],
        mix_weights: dict[LengthBucket, float],
        rng: random.Random | None = None,
    ) -> None:
        self._rng = rng or random.Random()
        self._groups: dict[LengthBucket, list[PromptRecord]] = {
            "short": [],
            "med": [],
            "long": [],
        }
        for prompt in prompts:
            if prompt.length_bucket is None:
                raise ValueError(f"Prompt {prompt.prompt_id} missing length_bucket")
            self._groups[prompt.length_bucket].append(prompt)

        if not any(self._groups.values()):
            raise ValueError("No prompts provided")

        self._active_buckets: list[LengthBucket] = []
        self._active_weights: list[float] = []
        for bucket in ("short", "med", "long"):
            weight = float(mix_weights.get(bucket, 0.0))
            if weight < 0:
                raise ValueError("mix weights must be non-negative")
            if not self._groups[bucket] or weight == 0:
                continue
            self._active_buckets.append(bucket)
            self._active_weights.append(weight)

        if not self._active_buckets:
            raise ValueError("No non-empty prompt buckets with positive weight")

    def sample(self) -> PromptRecord:
        bucket = self._rng.choices(self._active_buckets, weights=self._active_weights, k=1)[0]
        return self._rng.choice(self._groups[bucket])

    def sample_many(self, n: int) -> list[PromptRecord]:
        if n < 0:
            raise ValueError("n must be non-negative")
        return [self.sample() for _ in range(n)]


__all__ = ["PromptMixSampler"]
