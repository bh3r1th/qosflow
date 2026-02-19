from __future__ import annotations

import time

from fastapi import FastAPI
from pydantic import BaseModel, Field

from qosflow.common.config import ServerConfig
from qosflow.server.vllm_backend import VLLMBackend


class GenerateParams(BaseModel):
    temperature: float | None = None
    top_p: float | None = None
    max_new_tokens: int | None = None
    seed: int | None = None


class GenerateRequest(BaseModel):
    prompt: str
    params: GenerateParams = Field(default_factory=GenerateParams)


class GenerateResponse(BaseModel):
    text: str
    total_ms: float
    prefill_ms: None = None
    decode_ms: None = None
    batch_size: None = None


def create_app(config: ServerConfig) -> FastAPI:
    app = FastAPI(title="qosflow-vllm-server")

    @app.on_event("startup")
    def startup() -> None:
        app.state.backend = VLLMBackend(config)

    @app.post("/generate", response_model=GenerateResponse)
    def generate(req: GenerateRequest) -> GenerateResponse:
        params = req.params
        temperature = config.temperature if params.temperature is None else params.temperature
        top_p = config.top_p if params.top_p is None else params.top_p
        max_new_tokens = (
            config.max_new_tokens if params.max_new_tokens is None else params.max_new_tokens
        )
        seed = config.seed if params.seed is None else params.seed

        started = time.perf_counter()
        text = app.state.backend.generate(
            req.prompt,
            temperature=temperature,
            top_p=top_p,
            max_new_tokens=max_new_tokens,
            seed=seed,
        )
        total_ms = (time.perf_counter() - started) * 1000.0
        return GenerateResponse(text=text, total_ms=total_ms)

    return app
