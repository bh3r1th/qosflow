# Experiment protocol

## Invariants

- Keep decoding parameters fixed for all compared runs (`temperature`, `top_p`, `seed`, `max_new_tokens`).
- Keep model and runtime configuration fixed except for the batching control variable.
- Exclude warmup traffic from recorded traces and offline metrics.

## Conditions to run

Run at least these two conditions using the same prompts and offered load:

1. **Batching ON** (baseline): keep batching enabled (for example, `max_num_seqs: 16`, `max_num_batched_tokens: 2048`).
2. **Batching OFF** (control): disable effective batching by setting `max_num_seqs: 1` and `max_num_batched_tokens` to a single-request budget.

Keep all other settings unchanged between ON/OFF.

## Commands (Makefile targets)

### 1) Environment setup

```bash
make setup
```

### 2) Start server for a condition

```bash
make run-server
```

Before each run, set `configs/server.yaml` for either batching ON or OFF.

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
