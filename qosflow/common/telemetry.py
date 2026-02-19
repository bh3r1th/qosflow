from __future__ import annotations

import asyncio
import csv
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class NVMLSampler:
    def __init__(self, telemetry_interval_s: float = 0.5, gpu_index: int = 0) -> None:
        self.telemetry_interval_s = telemetry_interval_s
        self.gpu_index = gpu_index
        self._samples: list[dict[str, float | str | None]] = []
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._nvml_handle: Any | None = None
        self._nvml = None
        self._backend = self._init_backend()

    @property
    def samples(self) -> list[dict[str, float | str | None]]:
        return list(self._samples)

    def _init_backend(self) -> str:
        try:
            import pynvml  # type: ignore

            pynvml.nvmlInit()
            self._nvml = pynvml
            self._nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(self.gpu_index)
            return "pynvml"
        except Exception:  # noqa: BLE001
            self._nvml = None
            self._nvml_handle = None
            return "nvidia-smi"

    def _sample_pynvml(self) -> dict[str, float | str | None]:
        assert self._nvml is not None
        assert self._nvml_handle is not None

        util = self._nvml.nvmlDeviceGetUtilizationRates(self._nvml_handle)
        mem = self._nvml.nvmlDeviceGetMemoryInfo(self._nvml_handle)
        temp_c = float(
            self._nvml.nvmlDeviceGetTemperature(
                self._nvml_handle,
                self._nvml.NVML_TEMPERATURE_GPU,
            )
        )
        power_w: float | None = None
        try:
            power_mw = self._nvml.nvmlDeviceGetPowerUsage(self._nvml_handle)
            power_w = float(power_mw) / 1000.0
        except Exception:  # noqa: BLE001
            power_w = None

        return {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "gpu_util": float(util.gpu),
            "mem_used_mb": float(mem.used) / (1024.0 * 1024.0),
            "mem_total_mb": float(mem.total) / (1024.0 * 1024.0),
            "power_w": power_w,
            "temp_c": temp_c,
        }

    def _to_float(self, value: str) -> float | None:
        cleaned = value.strip()
        if not cleaned or cleaned.lower() in {"n/a", "not supported", "[not supported]"}:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _sample_nvidia_smi(self) -> dict[str, float | str | None] | None:
        cmd = [
            "nvidia-smi",
            f"--id={self.gpu_index}",
            "--query-gpu=utilization.gpu,memory.used,memory.total,power.draw,temperature.gpu",
            "--format=csv,noheader,nounits",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, check=True, text=True)
        except Exception:  # noqa: BLE001
            return None

        line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
        if not line:
            return None

        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 5:
            return None

        return {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "gpu_util": self._to_float(parts[0]),
            "mem_used_mb": self._to_float(parts[1]),
            "mem_total_mb": self._to_float(parts[2]),
            "power_w": self._to_float(parts[3]),
            "temp_c": self._to_float(parts[4]),
        }

    def _sample_once(self) -> dict[str, float | str | None] | None:
        if self._backend == "pynvml" and self._nvml is not None:
            try:
                return self._sample_pynvml()
            except Exception:  # noqa: BLE001
                self._backend = "nvidia-smi"

        return self._sample_nvidia_smi()

    async def _run(self) -> None:
        while self._running:
            sample = self._sample_once()
            if sample is not None:
                self._samples.append(sample)
            await asyncio.sleep(self.telemetry_interval_s)

    def start(self) -> None:
        if self._task is not None:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            await self._task
            self._task = None
        if self._nvml is not None:
            try:
                self._nvml.nvmlShutdown()
            except Exception:  # noqa: BLE001
                pass

    def write_csv(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "timestamp",
                    "gpu_util",
                    "mem_used_mb",
                    "mem_total_mb",
                    "power_w",
                    "temp_c",
                ],
            )
            writer.writeheader()
            writer.writerows(self._samples)


__all__ = ["NVMLSampler"]
