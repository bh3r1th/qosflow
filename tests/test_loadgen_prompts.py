from __future__ import annotations

from pathlib import Path

from qosflow.loadgen.prompts import LengthThresholds, assign_length_bucket, load_prompts


def test_assign_length_bucket_uses_thresholds() -> None:
    thresholds = LengthThresholds(short_max_chars=5, med_max_chars=10)
    assert assign_length_bucket("abc", thresholds) == "short"
    assert assign_length_bucket("abcdef", thresholds) == "med"
    assert assign_length_bucket("abcdefghijk", thresholds) == "long"


def test_load_prompts_assigns_buckets(tmp_path: Path) -> None:
    data = (
        '{"prompt_id":"p1","text":"tiny","tags":[],"expected":"ok"}\n'
        '{"prompt_id":"p2","text":"this is medium","tags":[]}\n'
    )
    path = tmp_path / "prompts.jsonl"
    path.write_text(data, encoding="utf-8")

    prompts = load_prompts(path, thresholds=LengthThresholds(short_max_chars=4, med_max_chars=20))

    assert [p.prompt_id for p in prompts] == ["p1", "p2"]
    assert [p.length_bucket for p in prompts] == ["short", "med"]
    assert prompts[0].expected == "ok"
