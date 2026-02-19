from __future__ import annotations

from itertools import combinations
from typing import Any

import pandas as pd


def _levenshtein_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            insertion = curr[j - 1] + 1
            deletion = prev[j] + 1
            substitution = prev[j - 1] + (0 if ca == cb else 1)
            curr.append(min(insertion, deletion, substitution))
        prev = curr
    return prev[-1]


def _normalized_edit_similarity(a: str, b: str) -> float:
    denom = max(len(a), len(b))
    if denom == 0:
        return 1.0
    return 1.0 - (_levenshtein_distance(a, b) / denom)


def _group_exact_match_rate(outputs: list[str]) -> float:
    if not outputs:
        return 0.0
    first = outputs[0]
    matches = sum(1 for item in outputs if item == first)
    return matches / len(outputs)


def _group_edit_similarity(outputs: list[str]) -> float:
    if len(outputs) < 2:
        return 1.0
    similarities = [_normalized_edit_similarity(a, b) for a, b in combinations(outputs, 2)]
    if not similarities:
        return 1.0
    return float(sum(similarities) / len(similarities))


def compute_stability_metrics(df: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    if df.empty:
        empty = {
            "stability_prompt_groups": 0,
            "stability_exact_match_rate": 0.0,
            "stability_edit_similarity": 0.0,
        }
        return empty, pd.DataFrame(columns=["prompt_id", "exact_match_rate", "edit_similarity"])

    output_col = "output_text" if "output_text" in df.columns else "output"
    if output_col not in df.columns or "prompt_id" not in df.columns:
        return {}, pd.DataFrame()

    work = df[["prompt_id", output_col]].copy()
    work[output_col] = work[output_col].fillna("").astype(str)

    rows: list[dict[str, Any]] = []
    for prompt_id, group in work.groupby("prompt_id"):
        outputs = list(group[output_col])
        rows.append(
            {
                "prompt_id": prompt_id,
                "exact_match_rate": _group_exact_match_rate(outputs),
                "edit_similarity": _group_edit_similarity(outputs),
            }
        )

    per_prompt = pd.DataFrame(rows).sort_values("prompt_id").reset_index(drop=True)
    metrics = {
        "stability_prompt_groups": int(len(per_prompt)),
        "stability_exact_match_rate": float(per_prompt["exact_match_rate"].mean())
        if not per_prompt.empty
        else 0.0,
        "stability_edit_similarity": float(per_prompt["edit_similarity"].mean())
        if not per_prompt.empty
        else 0.0,
    }
    return metrics, per_prompt


__all__ = ["compute_stability_metrics"]
