.PHONY: install install-dev test lint format notebooks fetch-markets fetch-history normalize research tree

UV ?= uv
PYTHON ?= python

install:
	$(UV) sync

install-dev:
	$(UV) sync --extra dev

test:
	$(UV) run pytest

lint:
	$(UV) run ruff check src tests scripts

format:
	$(UV) run ruff format src tests scripts

fetch-markets:
	$(UV) run python scripts/fetch_markets.py

fetch-history:
	$(UV) run python scripts/fetch_history.py

normalize:
	$(UV) run python scripts/normalize_data.py

research:
	$(UV) run python scripts/run_research.py

notebooks:
	$(UV) run jupyter lab notebooks

tree:
	@find . -type f \
		! -path './.git/*' \
		! -path './.venv/*' \
		! -path './__pycache__/*' \
		! -path './.pytest_cache/*' \
		! -path './.ruff_cache/*' \
		! -path './src/signalgraph.egg-info/*' \
		! -name '*.pyc' \
		| sort
