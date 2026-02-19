from __future__ import annotations

from fastapi.testclient import TestClient

from qosflow.common.config import ServerConfig
from qosflow.server.app import create_app
from qosflow.server.validate import resolve_server_config


class _FakeBackend:
    def __init__(self, _config: ServerConfig) -> None:
        self._config = _config

    def generate(self, _prompt: str, **_kwargs) -> str:  # noqa: ANN003
        return "ok"


def _cfg(dynamic_batching: bool) -> ServerConfig:
    return ServerConfig(
        host="127.0.0.1",
        port=8000,
        model="test-model",
        dtype="float16",
        max_new_tokens=16,
        temperature=0.0,
        top_p=1.0,
        seed=7,
        dynamic_batching=dynamic_batching,
        max_num_seqs=16,
        max_num_batched_tokens=2048,
        scheduler_delay_ms=5,
    )


def test_resolve_server_config_enforces_batching_off() -> None:
    effective, mode = resolve_server_config(_cfg(dynamic_batching=False))

    assert mode == "off"
    assert effective.max_num_seqs == 1
    assert effective.max_num_batched_tokens == 1
    assert effective.scheduler_delay_ms == 0


def test_generate_response_contains_batching_mode(monkeypatch) -> None:  # noqa: ANN001
    import qosflow.server.app as app_module

    monkeypatch.setattr(app_module, "VLLMBackend", _FakeBackend)
    app = create_app(_cfg(dynamic_batching=False))

    with TestClient(app) as client:
        res = client.post("/generate", json={"prompt": "hi", "params": {}})

    assert res.status_code == 200
    assert res.json()["batching_mode"] == "off"
