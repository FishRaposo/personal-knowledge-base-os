.PHONY: install dev test lint format typecheck docker-up docker-down demo migrate clean

install:
	pip install -e "../shared-core[dev,docparse]"
	pip install -r requirements.txt

migrate:
	alembic upgrade head

dev:
	python apps/api/src/main.py

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
