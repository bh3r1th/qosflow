from __future__ import annotations

import argparse

import pandas as pd


def detect_phase(input_path: str) -> str:
    df = pd.read_csv(input_path)
    p95 = float(df["latency_ms_p95"].iloc[0]) if "latency_ms_p95" in df and not df.empty else 0.0
    phase = "stable" if p95 < 500 else "degraded"
    print(phase)
    return phase


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    detect_phase(args.input)


if __name__ == "__main__":
    main()
