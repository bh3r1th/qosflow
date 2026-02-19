# Experiment protocol

## Invariants

- Keep decoding parameters fixed for all compared runs (`temperature`, `top_p`, `seed`, `max_new_tokens`).
- Keep model and runtime configuration fixed except for the batching control variable.
- Exclude warmup traffic from recorded traces and offline metrics.

## Conditions to run

Run at least these two conditions using the same prompts and offered load:

1. **Batching ON** (baseline): set `dynamic_batching: true` and use your intended batching knobs (for example, `max_num_seqs: 16`, `max_num_batched_tokens: 2048`).
2. **Batching OFF** (control): set `dynamic_batching: false`. The server enforces effective single-request behavior (`max_num_seqs=1`, `max_num_batched_tokens=1`, `scheduler_delay_ms=0`) regardless of configured knob values.

Keep all other settings unchanged between ON/OFF, and run both conditions for every experiment comparison.

## Commands (Makefile targets)

### 1) Environment setup

```bash
make setup
```

### 2) Start server for a condition

```bash
make run-server
```

Before each run, set `configs/server.yaml` for either `dynamic_batching: true` (ON) or `dynamic_batching: false` (OFF).

### 3) Generate load

```bash
make run-load
```

### 4) Evaluate metrics

```bash
make run-eval
```

### 5) Detect phase boundaries

```bash
make detect-phase
```

Repeat steps 2-5 for both batching conditions and compare the resulting metrics.
## Server-side validation and audit

At startup, `qosflow/server/validate.py` logs the effective batching mode and effective knobs.

Each `/generate` response includes `batching_mode` with value `"on"` or `"off"` to make the active mode explicit in online measurements.

