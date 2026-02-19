from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from qosflow.common.io import load_yaml


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ServerConfig(StrictBaseModel):
    host: str
    port: int
    model: str
    dtype: Literal["float16", "bfloat16"]
    max_new_tokens: int
    temperature: float
    top_p: float
    seed: int
    max_num_seqs: int
    max_num_batched_tokens: int
    scheduler_delay_ms: int


class LoadMixConfig(StrictBaseModel):
    short: float
    med: float
    long: float


class LoadGenConfig(StrictBaseModel):
    arrival_rate_rps: float
    concurrency: int
    duration_s: int
    warmup_s: int
    repeats: int
    prompt_source: Path
    mix: LoadMixConfig


class EvalConfig(StrictBaseModel):
    enable_embeddings: bool
    embedding_model: str


class ExperimentConfig(StrictBaseModel):
    name: str
    output_dir: Path


class QoSFlowConfig(StrictBaseModel):
    server: ServerConfig
    loadgen: LoadGenConfig
    eval: EvalConfig
    experiment: ExperimentConfig

    @classmethod
    def from_yaml(cls, path: str | Path) -> "QoSFlowConfig":
        return cls.model_validate(load_yaml(path))


__all__ = [
    "EvalConfig",
    "ExperimentConfig",
    "LoadGenConfig",
    "LoadMixConfig",
    "QoSFlowConfig",
    "ServerConfig",
    "load_yaml",
]
