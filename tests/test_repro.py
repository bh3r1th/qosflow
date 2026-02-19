from __future__ import annotations

import json
import random

from qosflow.common.repro import get_env_fingerprint, set_reproducible, write_manifest


def test_set_reproducible_resets_python_random() -> None:
    set_reproducible(123)
    first = [random.random() for _ in range(3)]

    set_reproducible(123)
    second = [random.random() for _ in range(3)]

    assert first == second


def test_write_manifest_includes_required_sections(tmp_path) -> None:
    path = tmp_path / "manifest.json"
    cfg = {"server": {"model": "demo"}}

    write_manifest(path, config=cfg)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert "timestamp" in payload
    assert "git_sha" in payload
    assert payload["config"] == cfg
    assert "env_fingerprint" in payload

    env = payload["env_fingerprint"]
    assert env == get_env_fingerprint() or isinstance(env, dict)
    assert "python_version" in env
    assert "platform" in env
