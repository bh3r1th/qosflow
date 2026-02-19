from __future__ import annotations

import argparse

from fastapi import FastAPI
from pydantic import BaseModel

from qosflow.common.config import load_yaml

app = FastAPI(title="qosflow-vllm-server")


class CompletionRequest(BaseModel):
    prompt: str
    max_tokens: int = 64


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/completions")
def completions(req: CompletionRequest) -> dict[str, str | int]:
    # Placeholder for vLLM integration.
    return {"text": req.prompt[: req.max_tokens], "tokens": min(len(req.prompt), req.max_tokens)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    cfg = load_yaml(args.config)

    import uvicorn

    uvicorn.run(
        "qosflow.server.app:app",
        host=cfg.get("host", "0.0.0.0"),
        port=int(cfg.get("port", 8000)),
        reload=bool(cfg.get("reload", False)),
    )


if __name__ == "__main__":
    main()
