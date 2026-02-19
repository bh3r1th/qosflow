from __future__ import annotations

import logging
from typing import Literal

from qosflow.common.config import ServerConfig

logger = logging.getLogger(__name__)

BatchingMode = Literal["on", "off"]


def resolve_server_config(config: ServerConfig) -> tuple[ServerConfig, BatchingMode]:
    """Return effective server config after enforcing batching mode constraints."""
    if config.dynamic_batching:
        return config, "on"

    effective = config.model_copy(
        update={
            "max_num_seqs": 1,
            "max_num_batched_tokens": 1,
            "scheduler_delay_ms": 0,
        }
    )
    return effective, "off"


def log_effective_batching(config: ServerConfig) -> tuple[ServerConfig, BatchingMode]:
    effective, mode = resolve_server_config(config)
    logger.info(
        "batching_mode=%s dynamic_batching=%s max_num_seqs=%d max_num_batched_tokens=%d scheduler_delay_ms=%d",
        mode,
        effective.dynamic_batching,
        effective.max_num_seqs,
        effective.max_num_batched_tokens,
        effective.scheduler_delay_ms,
    )
    return effective, mode


__all__ = ["BatchingMode", "log_effective_batching", "resolve_server_config"]
