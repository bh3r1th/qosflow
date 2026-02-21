# qosflow

## Quickstart

```bash
make setup
make run-server
make run-load
# Optional CLI overrides (keep --config mandatory)
python scripts/run_load.py --config configs/default.yaml --arrival-rate 8.0 --concurrency 32 --duration-s 120
```

See `docs/experiment_protocol.md` for the full experiment conditions and analysis commands.
