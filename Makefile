.PHONY: test lint clean backtest live install

install:
	pip install -e ".[dev]"

test:
	PYTHONPATH=src pytest tests/

lint:
	PYTHONPATH=src flake8 src/ tests/
	PYTHONPATH=src black --check src/ tests/
	PYTHONPATH=src isort --check-only src/ tests/

format:
	black src/ tests/
	isort src/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".eggs" -exec rm -rf {} +
	find . -type d -name "build" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +

backtest:
	python -m src.cli backtest

live:
	python -m src.cli live 