from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from qosflow.common.client import AsyncLLMClient, LLMClient


def test_async_client_generate_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/generate"
        body = json.loads(request.content.decode("utf-8"))
        assert body == {"prompt": "hello", "params": {"max_new_tokens": 8}}
        return httpx.Response(200, json={"text": "ok", "total_ms": 12.3})

    transport = httpx.MockTransport(handler)
    inner = httpx.AsyncClient(base_url="http://test", transport=transport, timeout=1.0)
    client = AsyncLLMClient("http://test", timeout=1.0, client=inner)

    text, timings, status = asyncio.run(client.generate("hello", {"max_new_tokens": 8}))

    assert text == "ok"
    assert status == 200
    assert timings["total_ms"] == 12.3
    assert timings["attempts"] == 1


def test_async_client_retries_503() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] < 3:
            return httpx.Response(503, json={"error": "busy"})
        return httpx.Response(200, json={"text": "done", "total_ms": 3.0})

    transport = httpx.MockTransport(handler)
    inner = httpx.AsyncClient(base_url="http://test", transport=transport, timeout=1.0)
    client = AsyncLLMClient(
        "http://test",
        timeout=1.0,
        max_retries=3,
        backoff_base_s=0.001,
        client=inner,
    )

    text, timings, status = asyncio.run(client.generate("p"))

    assert text == "done"
    assert status == 200
    assert calls["count"] == 3
    assert timings["attempts"] == 3


def test_async_client_raises_non_retriable_4xx() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "missing"})

    transport = httpx.MockTransport(handler)
    inner = httpx.AsyncClient(base_url="http://test", transport=transport, timeout=1.0)
    client = AsyncLLMClient("http://test", timeout=1.0, client=inner)

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(client.generate("p"))


def test_sync_wrapper() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"text": "sync", "total_ms": 1.0})

    transport = httpx.MockTransport(handler)

    class TestClient(LLMClient):
        def __init__(self) -> None:
            self._async_client = AsyncLLMClient(
                base_url="http://test",
                timeout=1.0,
                client=httpx.AsyncClient(base_url="http://test", transport=transport, timeout=1.0),
            )

    client = TestClient()
    text, _, status = client.generate("p")
    assert text == "sync"
    assert status == 200
