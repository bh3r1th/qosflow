#!/bin/bash
set -euo pipefail
cd /content/qosflow

# Kill zombie vLLM EngineCore if present
for pid in $(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | tr -d ' '); do
  kill -9 "$pid" || true
done

# Start server
nohup python -m uvicorn qosflow.server.entrypoint:app --host 127.0.0.1 --port 8000 > /content/server.log 2>&1 &
for i in $(seq 1 180); do
  ss -ltnp | grep -q ":8000" && break
  sleep 1
done
ss -ltnp | grep -q ":8000" || { echo "server didn't bind"; tail -n 200 /content/server.log; exit 1; }

# --- READINESS_PROBE ---
for i in $(seq 1 180); do
  code=$(curl -sS -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:8000/generate \
    -H "Content-Type: application/json" \
    -d '{"prompt":"ping","params":{"max_new_tokens":4}}' || true)
  if [ "$code" = "200" ]; then echo "READY (generate=200)"; break; fi
  sleep 1
done
code=$(curl -sS -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" -d '{"prompt":"ping","params":{"max_new_tokens":4}}' || true)
[ "$code" = "200" ] || { echo "server not ready (generate=$code)"; tail -n 200 /content/server.log; exit 1; }
# --- READINESS_PROBE ---


# Run a rate sweep
for RATE in 1 2 4 8 16 32 64 128 256 512; do
  sed -i "s/poisson_rate:.*/poisson_rate: $RATE/" configs/load.yaml
  python -m qosflow.loadgen.poisson --config configs/load.yaml
  mv load.out sweep_${RATE}.out
done
echo "done"

# --- CLEANUP ---
pkill -f "uvicorn.*qosflow.server.entrypoint" || true
sleep 1
for pid in $(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | tr -d ' '); do
  kill -9 "$pid" || true
done
