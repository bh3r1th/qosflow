import yaml
from qosflow.server.app import create_app
from qosflow.server.validate import ServerConfig

cfg = yaml.safe_load(open("/content/qosflow/configs/server.yaml", "r"))
config = ServerConfig(**cfg)
app = create_app(config)
