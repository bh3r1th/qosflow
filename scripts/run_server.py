from __future__ import annotations

import argparse

import uvicorn

from qosflow.common.config import ServerConfig, load_yaml
from qosflow.server.app import create_app


def load_server_config(path: str) -> ServerConfig:
    raw = load_yaml(path)
    if "server" in raw:
        raw = raw["server"]
    return ServerConfig.model_validate(raw)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    config = load_server_config(args.config)
    app = create_app(config)
    uvicorn.run(app, host=config.host, port=config.port)


if __name__ == "__main__":
    main()
