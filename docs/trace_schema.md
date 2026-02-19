# Trace schema (JSONL)

This document defines the JSONL records used by qosflow for prompt inputs and per-request traces.

## `PromptRecord`

Prompt catalog entries used by load generation.

| Field | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `prompt_id` | `string` | No | Stable identifier for joining with traces. |
| `text` | `string` | No | Prompt text sent to the server. |
| `tags` | `array[string]` | No | Free-form tags for filtering/slicing. Defaults to `[]`. |
| `expected` | `string` | Yes | Optional expected output/reference answer. |
| `length_bucket` | `"short" \| "med" \| "long"` | Yes | Optional coarse prompt-length class. |

## `TraceRecord` (versioned)

One line per request attempt. `version` is fixed to `"v1"`.

### Top-level fields

| Field | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `version` | `"v1"` | No | Schema version marker. |
| `request_id` | `string` | No | Unique request identifier. |
| `run_id` | `string` | No | Identifier for a complete loadgen run. |
| `prompt_id` | `string` | No | Foreign key to `PromptRecord.prompt_id`. |
| `repeat_idx` | `integer` | No | Repeat index for the same prompt under a run. |
| `ts_start_ns` | `integer` | No | Request start timestamp in nanoseconds. |
| `ts_end_ns` | `integer` | No | Request end timestamp in nanoseconds. |
| `total_ms` | `number` | No | End-to-end request latency in milliseconds. |
| `params` | `object` | No | Generation request parameters (see below). |
| `server` | `object` | No | Model/server snapshot used for the request (see below). |
| `system` | `object` | No | Runtime telemetry and HTTP outcome (see below). |
| `prompt_hash` | `string` | No | SHA-256 hash of normalized prompt text. |
| `output_hash` | `string` | No | SHA-256 hash of normalized output text. |
| `prompt_len_chars` | `integer` | No | Character length of prompt text. |
| `output_len_chars` | `integer` | No | Character length of output text. |
| `output_text` | `string` | No | Raw model output captured for evaluation. |

### `params`

| Field | Type | Nullable |
| --- | --- | --- |
| `temperature` | `number` | No |
| `top_p` | `number` | No |
| `seed` | `integer` | No |
| `max_new_tokens` | `integer` | No |

### `server`

| Field | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `model` | `string` | No | Deployed model identifier/name. |
| `dtype` | `string` | No | Server dtype used for the run. |
| `batching_knobs` | `object` | No | Snapshot of batching/scheduler knobs (key-value map). |

### `system`

| Field | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `http_status` | `integer` | No | HTTP status returned by serving endpoint. |
| `error` | `string` | Yes | Error string (if request failed). |
| `batch_size` | `integer` | Yes | Batch size observed by server/runtime, if available. |
| `queue_ms` | `number` | Yes | Queue wait latency in ms, if available. |
| `prefill_ms` | `number` | Yes | Prefill latency in ms, if available. |
| `decode_ms` | `number` | Yes | Decode latency in ms, if available. |

## Invariants

- `TraceRecord.version` must be `"v1"`.
- `ts_end_ns >= ts_start_ns`.
- `total_ms >= 0`.
- `prompt_id` in traces should refer to an existing prompt in the prompt catalog.
- `prompt_hash` and `output_hash` should be SHA-256 of normalized text (`NFKC`, normalized newlines, trimmed).
- `prompt_len_chars` and `output_len_chars` should match the captured text lengths used by the run.
