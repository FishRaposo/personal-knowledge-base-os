.PHONY: install dev test lint format typecheck docker-up docker-down demo migrate clean

install:
	python -m pip install -e ".[dev]"

migrate:
	alembic upgrade head

dev:
	python -m apps.api.src.main

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

typecheck:
	pyright apps/api/src/

docker-up:
	docker compose up -d

docker-down:
	docker compose down

demo:
	python examples/run_demo.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
