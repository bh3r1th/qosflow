from __future__ import annotations

import argparse

import pandas as pd


def evaluate(input_path: str, output_path: str) -> None:
    df = pd.read_csv(input_path)
    out = pd.DataFrame(
        {
            "count": [len(df)],
            "latency_ms_p50": [df["latency_ms"].quantile(0.5) if "latency_ms" in df else 0],
            "latency_ms_p95": [df["latency_ms"].quantile(0.95) if "latency_ms" in df else 0],
        }
    )
    out.to_csv(output_path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    evaluate(args.input, args.output)


if __name__ == "__main__":
    main()
