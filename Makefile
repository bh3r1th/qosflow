PYTHON ?= python3

setup:
	$(PYTHON) -m pip install -U pip
	$(PYTHON) -m pip install -e .[dev]

format:
	ruff format .

lint:
	ruff check .

typecheck:
	mypy qosflow

test:
	pytest

run-server:
	$(PYTHON) -m qosflow.server.app --config configs/server.yaml

run-load:
	$(PYTHON) -m qosflow.loadgen.poisson --config configs/load.yaml

run-eval:
	$(PYTHON) -m qosflow.metrics.evaluate --input data/requests.csv --output data/metrics.csv

detect-phase:
	$(PYTHON) -m qosflow.analysis.phase --input data/metrics.csv

run-sweep:
	$(PYTHON) scripts/run_sweep.py --config configs/sweep.yaml
