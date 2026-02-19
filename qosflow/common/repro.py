from __future__ import annotations

import json
import platform
import random
import subprocess
import sys
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any


def get_git_sha() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except Exception:  # noqa: BLE001
        return None
    sha = out.strip()
    return sha or None


def _package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _driver_version() -> str | None:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except Exception:  # noqa: BLE001
        return None
    line = out.splitlines()[0].strip() if out else ""
    return line or None


def get_env_fingerprint() -> dict[str, Any]:
    info: dict[str, Any] = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "vllm_version": _package_version("vllm"),
        "torch_version": _package_version("torch"),
        "cuda_version": None,
        "driver_version": _driver_version(),
    }
    try:
        import torch

        info["cuda_version"] = torch.version.cuda
    except Exception:  # noqa: BLE001
        pass
    return info


def set_reproducible(seed: int) -> None:
    random.seed(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except Exception:  # noqa: BLE001
        pass
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        try:
            torch.use_deterministic_algorithms(True, warn_only=True)
        except TypeError:
            torch.use_deterministic_algorithms(True)
    except Exception:  # noqa: BLE001
        pass


def write_manifest(path: Path, *, config: dict[str, Any]) -> None:
    payload = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "git_sha": get_git_sha(),
        "config": config,
        "env_fingerprint": get_env_fingerprint(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


__all__ = [
    "get_env_fingerprint",
    "get_git_sha",
    "set_reproducible",
    "write_manifest",
]
