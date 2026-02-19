from __future__ import annotations

import argparse
import json

from qosflow.common.config import QoSFlowConfig
from qosflow.common.io import load_yaml


def main() -> None:
    parser = argparse.ArgumentParser(description="Load, validate, and print qosflow config.")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    args = parser.parse_args()

    raw = load_yaml(args.config)
    config = QoSFlowConfig.model_validate(raw)
    print(json.dumps(config.model_dump(mode="json"), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
