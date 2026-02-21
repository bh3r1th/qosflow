#!/usr/bin/env bash
set -euo pipefail

# ---- Config (edit only these) ----
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
APP="${APP:-qosflow.server.entrypoint:app}"
BASE_URL="http://${HOST}:${PORT}"

MODEL_PROMPT="${MODEL_PROMPT:-hello}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-16}"

CONFIG_IN="${CONFIG_IN:-configs/load.yaml}"
DURATION_S="${DURATION_S:-60}"     # per-rate duration
TIMEOUT_S="${TIMEOUT_S:-30}"
RATES="${RATES:-1 2 3 4 5 6 8 10 12 15 20}"

RUN_ID="${RUN_ID:-$(date +%Y%m%d_%H%M%S)}"
OUT_DIR="${OUT_DIR:-runs/${RUN_ID}}"

# ---- Helpers ----
need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }; }
need python
need curl

[[ -f "${CONFIG_IN}" ]] || { echo "Missing ${CONFIG_IN} (run from repo root)" >&2; exit 1; }

mkdir -p "${OUT_DIR}"

SERVER_PID=""
DMON_PID=""

cleanup() {
  set +e
  if [[ -n "${DMON_PID}" ]]; then kill "${DMON_PID}" >/dev/null 2>&1 || true; fi
  if [[ -n "${SERVER_PID}" ]]; then kill "${SERVER_PID}" >/dev/null 2>&1 || true; fi
}
trap cleanup EXIT INT TERM

echo "RUN_ID=${RUN_ID}"
echo "OUT_DIR=${OUT_DIR}"
echo "RATES=${RATES}"
echo "DURATION_S=${DURATION_S}"

# ---- Start server ----
echo "[1/6] Starting server..."
# Ensure port is free (avoid bind: address already in use)
if command -v fuser >/dev/null 2>&1; then
  sudo fuser -k ${PORT}/tcp >/dev/null 2>&1 || true
else
  pkill -f "uvicorn .*${PORT}" >/dev/null 2>&1 || true
fi
nohup uvicorn "${APP}" --host "${HOST}" --port "${PORT}" > "${OUT_DIR}/server.log" 2>&1 &
SERVER_PID="$!"

# ---- Readiness (POST /generate until 200) ----
echo "[2/6] Waiting for readiness on ${BASE_URL}/generate ..."
READY=0
for _ in $(seq 1 240); do
  CODE="$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/generate" \
    -H "Content-Type: application/json" \
    -d "{\"prompt\":\"${MODEL_PROMPT}\",\"params\":{\"max_new_tokens\":${MAX_NEW_TOKENS}}}" || true)"
  if [[ "${CODE}" == "200" ]]; then
    READY=1
    break
  fi
  # If server died, fail fast with last logs
  if ! kill -0 "${SERVER_PID}" >/dev/null 2>&1; then
    echo "Server process exited before readiness." >&2
    tail -n 200 "${OUT_DIR}/server.log" >&2 || true
    exit 1
  fi
  sleep 0.25
done
[[ "${READY}" -eq 1 ]] || { echo "Readiness timeout (last HTTP=${CODE})." >&2; tail -n 200 "${OUT_DIR}/server.log" >&2 || true; exit 1; }
echo "Ready."

# ---- Optional GPU logging ----
if command -v nvidia-smi >/dev/null 2>&1; then
  echo "[3/6] Starting GPU dmon logging..."
  nohup nvidia-smi dmon -s pucvmet -d 1 > "${OUT_DIR}/gpu_dmon.log" 2>&1 &
  DMON_PID="$!"
else
  echo "[3/6] nvidia-smi not found; skipping GPU dmon."
fi

# ---- Copy immutable config snapshot ----
cp -f "${CONFIG_IN}" "${OUT_DIR}/load.yaml.orig"

# ---- Sweep ----
echo "[4/6] Running sweep..."
for r in ${RATES}; do
  RATE_DIR="${OUT_DIR}/rate_${r}"
  mkdir -p "${RATE_DIR}"

  # Make a temp config per-rate (no tracked file mutation)
  python - <<PY
import yaml, pathlib
cfg_path = pathlib.Path("${OUT_DIR}") / "load.yaml.orig"
out_path = pathlib.Path("${RATE_DIR}") / "load.yaml"
cfg = yaml.safe_load(cfg_path.read_text())

# keys confirmed from poisson.py: target_url, timeout_s, duration_s, poisson_rate
cfg["target_url"] = "${BASE_URL}"
cfg["timeout_s"] = float(${TIMEOUT_S})
cfg["duration_s"] = float(${DURATION_S})
cfg["poisson_rate"] = float(${r})

# keep endpoint if present (you previously set cfg["endpoint"]="/generate")
cfg["endpoint"] = cfg.get("endpoint", "/generate")

out_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
print(f"Wrote {out_path}")
PY

  echo "=== RATE ${r} ==="
  rm -f load.out 2>/dev/null || true

  # Run loadgen and capture logs
  set +e
  python -m qosflow.loadgen.poisson --config "${RATE_DIR}/load.yaml" > "${RATE_DIR}/loadgen.log" 2>&1
  RC=$?
  set -e

  # Move raw data if present
  if [[ -f load.out ]]; then
    mv -f load.out "${RATE_DIR}/load.out"
  fi

  # Basic health check: server still alive
  if ! kill -0 "${SERVER_PID}" >/dev/null 2>&1; then
    echo "Server died during rate ${r}." >&2
    tail -n 200 "${OUT_DIR}/server.log" >&2 || true
    exit 1
  fi

  # If loadgen failed, record it and stop sweep (don’t continue producing junk)
  if [[ "${RC}" -ne 0 ]]; then
    echo "Loadgen failed at rate ${r} (exit ${RC}). Stopping sweep." >&2
    exit 1
  fi

  # Quick per-rate sanity: require at least 1 line
  if [[ ! -s "${RATE_DIR}/load.out" ]]; then
    echo "No load captured at rate ${r}. Stopping sweep." >&2
    tail -n 80 "${RATE_DIR}/loadgen.log" >&2 || true
    exit 1
  fi
done

echo "[5/6] Sweep complete."

# ---- Summarize ----
echo "[6/6] Summarizing..."
python tools/summarize_runs.py "${OUT_DIR}" | tee "${OUT_DIR}/summary.txt"
echo "Wrote: ${OUT_DIR}/summary.txt"
echo "Wrote: ${OUT_DIR}/summary.md"
echo "Wrote: ${OUT_DIR}/results.csv"

