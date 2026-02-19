from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _token_f1(pred: str, ref: str) -> float:
    pred_tokens = pred.split()
    ref_tokens = ref.split()

    if not pred_tokens and not ref_tokens:
        return 1.0
    if not pred_tokens or not ref_tokens:
        return 0.0

    pred_counts = Counter(pred_tokens)
    ref_counts = Counter(ref_tokens)
    overlap = sum((pred_counts & ref_counts).values())
    if overlap == 0:
        return 0.0

    precision = overlap / len(pred_tokens)
    recall = overlap / len(ref_tokens)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def compute_task_metrics(df: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
    if "expected" not in df.columns:
        return {}, pd.DataFrame()

    eval_df = df[df["expected"].notna()].copy()
    if eval_df.empty:
        return {}, pd.DataFrame()

    output_col = "output_text" if "output_text" in eval_df.columns else "output"
    eval_df["expected_norm"] = eval_df["expected"].apply(_normalize_text)
    if output_col in eval_df.columns:
        eval_df["output_norm"] = eval_df[output_col].apply(_normalize_text)
    else:
        eval_df["output_norm"] = ""

    eval_df["exact_match"] = (eval_df["expected_norm"] == eval_df["output_norm"]).astype(float)
    eval_df["token_f1"] = eval_df.apply(
        lambda row: _token_f1(row["output_norm"], row["expected_norm"]), axis=1
    )

    metrics = {
        "task_count": int(len(eval_df)),
        "task_exact_match": float(eval_df["exact_match"].mean()),
        "task_token_f1": float(eval_df["token_f1"].mean()),
    }
    per_row = eval_df[["prompt_id", "repeat_idx", "exact_match", "token_f1"]].reset_index(drop=True)
    return metrics, per_row


__all__ = ["compute_task_metrics"]
