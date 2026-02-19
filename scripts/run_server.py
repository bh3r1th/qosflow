from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from qosflow.common.config import ServerConfig, load_yaml
from qosflow.common.repro import get_env_fingerprint, set_reproducible, write_manifest
from qosflow.server.app import create_app


def load_server_config(path: str) -> ServerConfig:
    raw = load_yaml(path)
    if "server" in raw:
        raw = raw["server"]
    return ServerConfig.model_validate(raw)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--manifest-path", default=None)
    args = parser.parse_args()

    config = load_server_config(args.config)
    set_reproducible(config.seed)

    env_fingerprint = get_env_fingerprint()
    print(f"env_fingerprint={env_fingerprint}")

    if args.manifest_path:
        write_manifest(
            path=Path(args.manifest_path),
            config={"server": config.model_dump(mode="json")},
        )

    app = create_app(config)
    uvicorn.run(app, host=config.host, port=config.port)


if __name__ == "__main__":
    main()
