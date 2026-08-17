.PHONY: install dev test lint format format-check typecheck forbidden docker-check docker-up docker-down demo evidence migrate release-check clean

install:
	python -m pip install -e ".[dev]"

migrate:
	alembic upgrade head

dev:
	python -m apps.api.src.main

test:
	pytest

lint:
	python -m ruff check apps/api/src tests examples scripts alembic

format:
	python -m ruff format apps/api/src tests examples scripts alembic

format-check:
	python -m ruff format --check apps/api/src tests examples scripts alembic

typecheck:
	python -m pyright apps/api/src

forbidden:
	python scripts/check_forbidden_dependencies.py

docker-check:
	docker compose config
	docker compose build web

docker-up:
	docker compose up -d

docker-down:
	docker compose down

demo:
	python examples/run_demo.py

evidence:
	python scripts/portfolio_demo.py
	python scripts/verify_portfolio_evidence.py

release-check: forbidden lint format-check typecheck test migrate evidence

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
