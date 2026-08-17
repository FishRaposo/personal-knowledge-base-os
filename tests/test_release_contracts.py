"""Executable contracts for the offline release and CI surface."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ci_runs_every_default_offline_release_gate() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    required_commands = (
        'python -m pip install -e ".[dev]"',
        "python -m pytest -q",
        "python -m ruff check apps/api/src tests examples scripts alembic",
        "python -m ruff format --check apps/api/src tests examples scripts alembic",
        "python -m pyright apps/api/src",
        "python scripts/check_forbidden_dependencies.py",
        "python -m alembic upgrade head",
        "python scripts/portfolio_demo.py",
        "python scripts/verify_portfolio_evidence.py",
        "python -m build",
        "python scripts/check_wheel_contents.py",
        "npm ci",
        "npm test -- --run",
        "npm exec tsc -- --noEmit",
        "npm run lint",
        "npm run build",
        "docker compose config",
        "docker compose build web",
    )

    missing = [command for command in required_commands if command not in workflow]
    assert not missing, f"CI is missing offline release gates: {missing}"
    assert "working-directory: apps/web" in workflow
    assert "DATABASE_URL: sqlite:///" in workflow


def test_ci_labels_chromium_as_an_explicit_optional_gate() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "run_playwright:" in workflow
    assert "npx playwright install --with-deps chromium" in workflow
    assert "npm run test:e2e -- --project=chromium" in workflow
    assert "if: inputs.run_playwright" in workflow


def test_production_web_image_uses_standalone_output_without_dev_dependencies() -> None:
    dockerfile = (ROOT / "apps" / "web" / "Dockerfile").read_text(encoding="utf-8")
    next_config = (ROOT / "apps" / "web" / "next.config.js").read_text(encoding="utf-8")

    runner = dockerfile.split(" AS runner", maxsplit=1)[1]
    assert ".next/standalone" in runner
    assert 'CMD ["node", "server.js"]' in runner
    assert "node_modules" not in runner
    assert 'output: "standalone"' in next_config


def test_forbidden_scanner_rejects_dependency_and_secret_fixtures(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "bad.py"
    fixture.write_text(
        "from "
        + "shared_core import config\n"
        + "TOKEN = 'ghp_123456789012345678901234567890123456'\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "check_forbidden_dependencies.py"),
            "--root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "external shared-core import" in result.stdout
    assert "GitHub personal access token" in result.stdout


def test_forbidden_scanner_accepts_offline_internal_imports(tmp_path: Path) -> None:
    fixture = tmp_path / "good.py"
    fixture.write_text(
        "from apps.api.src.internal.vendor_core import config\nOPENAI_API_KEY = None\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "check_forbidden_dependencies.py"),
            "--root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "No forbidden dependencies or committed secrets found." in result.stdout
