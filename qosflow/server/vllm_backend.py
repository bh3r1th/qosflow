from __future__ import annotations

from typing import Any

from qosflow.common.config import ServerConfig


class VLLMBackend:
    def __init__(self, config: ServerConfig) -> None:
        self._config = config

        from vllm import LLM

        self._llm = LLM(
        gpu_memory_utilization=0.75,
            model=config.model,
            dtype=config.dtype,
            max_num_seqs=config.max_num_seqs,
            max_num_batched_tokens=config.max_num_batched_tokens,
        )

    def generate(
        self,
        prompt: str,
        *,
        temperature: float,
        top_p: float,
        max_new_tokens: int,
        seed: int,
    ) -> str:
        from vllm import SamplingParams

        sampling_params = SamplingParams(
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_new_tokens,
            seed=seed,
        )
        outputs: list[Any] = self._llm.generate([prompt], sampling_params=sampling_params)
        if not outputs:
            return ""
        completion = outputs[0]
        if not completion.outputs:
            return ""
        return completion.outputs[0].text
