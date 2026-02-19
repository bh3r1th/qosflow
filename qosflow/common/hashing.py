from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any


def normalize_text(value: str) -> str:
    """Normalize text before hashing to keep digests stable across platforms."""
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.strip()


def sha256_normalized_text(value: str) -> str:
    """Return SHA256 digest for normalized text input."""
    normalized = normalize_text(value)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def sha256_normalized_json(value: Any) -> str:
    """Return SHA256 digest for a canonical JSON serialization."""
    canonical = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "normalize_text",
    "sha256_normalized_json",
    "sha256_normalized_text",
]
