from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PromptRecord(StrictBaseModel):
    prompt_id: str
    text: str
    tags: list[str] = Field(default_factory=list)
    expected: str | None = None
    length_bucket: Literal["short", "med", "long"] | None = None


class TraceParams(StrictBaseModel):
    temperature: float
    top_p: float
    seed: int
    max_new_tokens: int


class TraceServerSnapshot(StrictBaseModel):
    model: str
    dtype: str
    batching_knobs: dict[str, Any] = Field(default_factory=dict)


class TraceSystem(StrictBaseModel):
    http_status: int
    error: str | None = None
    batch_size: int | None = None
    queue_ms: float | None = None
    prefill_ms: float | None = None
    decode_ms: float | None = None


class TraceRecord(StrictBaseModel):
    version: Literal["v1"] = "v1"
    request_id: str
    run_id: str
    prompt_id: str
    repeat_idx: int

    ts_start_ns: int
    ts_end_ns: int
    total_ms: float

    params: TraceParams
    server: TraceServerSnapshot
    system: TraceSystem

    prompt_hash: str
    output_hash: str

    prompt_len_chars: int
    output_len_chars: int
    output_text: str

    @model_validator(mode="after")
    def validate_timing(self) -> "TraceRecord":
        if self.ts_end_ns < self.ts_start_ns:
            raise ValueError("ts_end_ns must be greater than or equal to ts_start_ns")
        if self.total_ms < 0:
            raise ValueError("total_ms must be non-negative")
        return self


__all__ = [
    "PromptRecord",
    "TraceParams",
    "TraceRecord",
    "TraceServerSnapshot",
    "TraceSystem",
]
