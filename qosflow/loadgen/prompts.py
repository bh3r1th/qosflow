from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from qosflow.common.io import read_jsonl
from qosflow.common.schema import PromptRecord

LengthBucket = Literal["short", "med", "long"]


@dataclass(frozen=True)
class LengthThresholds:
    short_max_chars: int = 160
    med_max_chars: int = 480

    def __post_init__(self) -> None:
        if self.short_max_chars < 0:
            raise ValueError("short_max_chars must be non-negative")
        if self.med_max_chars < self.short_max_chars:
            raise ValueError("med_max_chars must be >= short_max_chars")


def assign_length_bucket(
    text: str,
    thresholds: LengthThresholds | None = None,
) -> LengthBucket:
    limits = thresholds or LengthThresholds()
    length = len(text)
    if length <= limits.short_max_chars:
        return "short"
    if length <= limits.med_max_chars:
        return "med"
    return "long"


def load_prompts(
    path: str | Path,
    thresholds: LengthThresholds | None = None,
) -> list[PromptRecord]:
    limits = thresholds or LengthThresholds()
    records: list[PromptRecord] = []
    for row in read_jsonl(path):
        text = str(row.get("text", ""))
        payload = dict(row)
        payload["length_bucket"] = assign_length_bucket(text, limits)
        records.append(PromptRecord.model_validate(payload))
    return records


__all__ = [
    "LengthBucket",
    "LengthThresholds",
    "assign_length_bucket",
    "load_prompts",
]
