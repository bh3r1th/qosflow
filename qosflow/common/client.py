from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Mapping
from typing import Any

import httpx


class AsyncLLMClient:
    def __init__(
        self,
        base_url: str,
        timeout: float,
        *,
        max_retries: int = 3,
        backoff_base_s: float = 0.2,
        backoff_max_s: float = 5.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_base_s = backoff_base_s
        self._backoff_max_s = backoff_max_s
        self._client = client
        self._owns_client = client is None

    async def generate(
        self,
        prompt: str,
        params: Mapping[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any], int]:
        payload = {"prompt": prompt, "params": dict(params or {})}

        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout)
        started = time.perf_counter()

        attempt = 0
        while True:
            response = await self._client.post("/generate", json=payload)
            status = response.status_code

            if status in (429, 503) and attempt < self._max_retries:
                delay = min(self._backoff_base_s * (2**attempt), self._backoff_max_s)
                await asyncio.sleep(delay + random.uniform(0.0, delay * 0.1))
                attempt += 1
                continue

            if 400 <= status < 500 and status != 429:
                response.raise_for_status()

            response.raise_for_status()
            body = response.json()
            text = str(body.get("text", ""))
            timings = {
                "total_ms": body.get("total_ms"),
                "prefill_ms": body.get("prefill_ms"),
                "decode_ms": body.get("decode_ms"),
                "attempts": attempt + 1,
                "elapsed_ms": (time.perf_counter() - started) * 1000.0,
            }
            return text, timings, status

    async def aclose(self) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()


class LLMClient:
    def __init__(
        self,
        base_url: str,
        timeout: float,
        *,
        max_retries: int = 3,
        backoff_base_s: float = 0.2,
        backoff_max_s: float = 5.0,
    ) -> None:
        self._async_client = AsyncLLMClient(
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            backoff_base_s=backoff_base_s,
            backoff_max_s=backoff_max_s,
        )

    def generate(
        self,
        prompt: str,
        params: Mapping[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any], int]:
        return asyncio.run(self._async_client.generate(prompt, params=params))


__all__ = ["AsyncLLMClient", "LLMClient"]
