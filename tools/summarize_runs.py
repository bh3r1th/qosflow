#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

def pct(xs: List[float], p: float) -> float:
    if not xs:
        return float("nan")
    xs_sorted = sorted(xs)
    k = (len(xs_sorted) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return xs_sorted[int(k)]
    d0 = xs_sorted[f] * (c - k)
    d1 = xs_sorted[c] * (k - f)
    return d0 + d1

def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows

def compute_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(rows)
    ok = [r for r in rows if int(r.get("status_code", 0)) == 200]
    err = total - len(ok)

    lat = [float(r["elapsed_ms"]) for r in ok if "elapsed_ms" in r and r["elapsed_ms"] is not None]
    ts = [int(r["ts_recv_ns"]) for r in ok if "ts_recv_ns" in r and r["ts_recv_ns"] is not None]

    span_s = (max(ts) - min(ts)) / 1e9 if len(ts) >= 2 else float("nan")
    achieved_rps = (len(ok) / span_s) if span_s and not math.isnan(span_s) and span_s > 0 else float("nan")
    err_rate = (err / total) if total > 0 else float("nan")

    out = {
        "total": total,
        "ok": len(ok),
        "err": err,
        "err_rate": err_rate,
        "span_s": span_s,
        "achieved_rps": achieved_rps,
        "p50_ms": pct(lat, 50),
        "p95_ms": pct(lat, 95),
        "p99_ms": pct(lat, 99),
        "mean_ms": (statistics.mean(lat) if lat else float("nan")),
    }
    return out

def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: summarize_runs.py runs/<RUN_ID>", file=sys.stderr)
        return 2

    run_dir = Path(sys.argv[1]).resolve()
    if not run_dir.exists():
        print(f"Missing run dir: {run_dir}", file=sys.stderr)
        return 2

    rate_dirs = sorted([p for p in run_dir.glob("rate_*") if p.is_dir()],
                       key=lambda p: float(p.name.split("_", 1)[1]))
    if not rate_dirs:
        print(f"No rate_* dirs in {run_dir}", file=sys.stderr)
        return 2

    results: List[Dict[str, Any]] = []
    for rd in rate_dirs:
        rate = float(rd.name.split("_", 1)[1])
        load_path = rd / "load.out"
        if not load_path.exists():
            continue
        rows = read_jsonl(load_path)
        m = compute_metrics(rows)
        m["offered_rate"] = rate
        results.append(m)

    if not results:
        print("No load.out found.", file=sys.stderr)
        return 2

    # Write CSV
    csv_path = run_dir / "results.csv"
    fields = ["offered_rate", "achieved_rps", "span_s", "p50_ms", "p95_ms", "p99_ms", "err_rate", "ok", "err", "total"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results:
            w.writerow({k: r.get(k) for k in fields})

    # Identify plateau (max achieved_rps) and first overload-ish point (err_rate>1% or p99>3x p50)
    best = max(results, key=lambda r: (r["achieved_rps"] if not math.isnan(r["achieved_rps"]) else -1.0))
    overload = None
    for r in sorted(results, key=lambda x: x["offered_rate"]):
        if (not math.isnan(r["err_rate"]) and r["err_rate"] > 0.01) or (
            not math.isnan(r["p99_ms"]) and not math.isnan(r["p50_ms"]) and r["p50_ms"] > 0 and r["p99_ms"] > 3.0 * r["p50_ms"]
        ):
            overload = r
            break

    # Markdown summary
    md_path = run_dir / "summary.md"
    lines: List[str] = []
    lines.append(f"# vLLM QoSFlow PoC Benchmark Summary ({run_dir.name})")
    lines.append("")
    lines.append("## Key results")
    lines.append(f"- Peak achieved RPS: **{best['achieved_rps']:.2f}** at offered rate **{best['offered_rate']:.2f}**")
    lines.append(f"- Peak latency at peak RPS: p50 **{best['p50_ms']:.1f} ms**, p95 **{best['p95_ms']:.1f} ms**, p99 **{best['p99_ms']:.1f} ms**")
    if overload:
        lines.append(f"- First overload signal at offered rate **{overload['offered_rate']:.2f}** (err_rate={overload['err_rate']*100:.2f}%, p99={overload['p99_ms']:.1f} ms)")
    else:
        lines.append("- No overload signal detected by simple heuristics (err_rate<=1% and p99 not exploding).")
    lines.append("")
    lines.append("## Sweep table")
    lines.append("")
    lines.append("| offered_rate | achieved_rps | span_s | p50_ms | p95_ms | p99_ms | err_% | ok | err | total |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in sorted(results, key=lambda x: x["offered_rate"]):
        err_pct = (r["err_rate"] * 100.0) if not math.isnan(r["err_rate"]) else float("nan")
        lines.append(
            f"| {r['offered_rate']:.2f} | {r['achieved_rps']:.2f} | {r['span_s']:.1f} | {r['p50_ms']:.1f} | {r['p95_ms']:.1f} | {r['p99_ms']:.1f} | {err_pct:.2f} | {r['ok']} | {r['err']} | {r['total']} |"
        )
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    # Print tight console summary
    print("RATE_SWEEP_SUMMARY")
    for r in sorted(results, key=lambda x: x["offered_rate"]):
        err_pct = (r["err_rate"] * 100.0) if not math.isnan(r["err_rate"]) else float("nan")
        print(f"rate={r['offered_rate']:.2f}  achieved={r['achieved_rps']:.2f} rps  p50={r['p50_ms']:.1f}ms p95={r['p95_ms']:.1f}ms p99={r['p99_ms']:.1f}ms  err={err_pct:.2f}%  n={r['total']}")
    print(f"\nWROTE {csv_path}")
    print(f"WROTE {md_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
