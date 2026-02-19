from __future__ import annotations

import argparse

from qosflow.common.config import load_yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    cfg = load_yaml(args.config)
    experiments = cfg.get("experiments", [])
    print(f"planned experiments: {len(experiments)}")


if __name__ == "__main__":
    main()
