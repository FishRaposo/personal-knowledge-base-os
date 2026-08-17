"""Contracts that keep the API install self-contained and reproducible."""

from __future__ import annotations

import importlib
import os
import runpy
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR_PACKAGE = "apps.api.src.internal.vendor_core"
VENDORED_MODULES = (
    "config",
    "database",
    "docparse",
    "embeddings",
    "errors",
    "evaljudge",
    "health",
    "llm",
    "logging",
    "pricing",
    "redis",
    "tasks",
    "testing",
    "vectorstore",
)


def test_runtime_imports_use_only_the_internal_vendor_namespace() -> None:
    """The default API path must not import an external ``shared_core`` package."""

    external_namespace = "shared" + "_core"
    sys.modules.pop(external_namespace, None)
    for module in VENDORED_MODULES:
        imported = importlib.import_module(f"{VENDOR_PACKAGE}.{module}")
        assert imported.__name__ == f"{VENDOR_PACKAGE}.{module}"

    for module in (
        "apps.api.src.config",
        "apps.api.src.db",
        "apps.api.src.models",
        "apps.api.src.indexer",
        "apps.api.src.embeddings",
        "apps.api.src.search",
        "apps.api.src.chat",
        "apps.api.src.worker",
        "apps.api.src.main",
    ):
        importlib.import_module(module)

    assert external_namespace not in sys.modules


def test_actionable_files_do_not_restore_the_archived_dependency() -> None:
    """Source, automation, and setup docs cannot point back to the sibling package."""

    git_install_prefix = "git+https://github.com/FishRaposo/"
    archived_package = "operator" + "-shared-core"
    patterns = (
        "from " + "shared_core",
        "import " + "shared_core",
        "../" + "shared-core",
        git_install_prefix + archived_package,
    )
    paths = [
        ROOT / "apps" / "api",
        ROOT / "tests",
        ROOT / "alembic",
        ROOT / ".github",
        ROOT / "Makefile",
        ROOT / "README.md",
        ROOT / "AGENTS.md",
        ROOT / "requirements.txt",
    ]
    violations: list[str] = []
    for path in paths:
        candidates = path.rglob("*") if path.is_dir() else (path,)
        for candidate in candidates:
            if candidate == Path(__file__):
                continue
            if not candidate.is_file() or "__pycache__" in candidate.parts:
                continue
            try:
                text = candidate.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for pattern in patterns:
                if pattern in text:
                    violations.append(f"{candidate.relative_to(ROOT)}: {pattern}")

    assert violations == []


def test_wheel_contents_checker_covers_the_vendor_namespace() -> None:
    checker_path = ROOT / "scripts" / "check_wheel_contents.py"
    namespace = runpy.run_path(str(checker_path))
    required = set(namespace["REQUIRED_MEMBERS"])

    assert "apps/api/src/internal/vendor_core/config.py" in required
    assert "apps/api/src/internal/vendor_core/vectorstore.py" in required
    assert callable(namespace["verify_isolated_install"])
    isolated_imports = set(namespace["ISOLATED_IMPORTS"])
    assert "apps.api.src.main" in isolated_imports
    assert "apps.api.src.worker" in isolated_imports
    assert "apps.api.src.internal.vendor_core.evaljudge" in isolated_imports


def test_runtime_docstrings_use_the_owned_vendor_name() -> None:
    """Runtime guidance must not describe the archived import namespace as live."""

    stale_name = "shared" + "_core"
    violations: list[str] = []
    for candidate in (ROOT / "apps" / "api" / "src").rglob("*.py"):
        text = candidate.read_text(encoding="utf-8")
        if stale_name in text:
            violations.append(str(candidate.relative_to(ROOT)))

    assert violations == []


def test_alembic_upgrade_uses_installed_package_imports(tmp_path: Path) -> None:
    """Migrations must import the same package namespace as the application."""

    database = tmp_path / "migration.db"
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite:///{database.as_posix()}"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert database.exists()


def test_worker_and_api_import_without_redis_or_celery() -> None:
    """Optional infrastructure packages cannot be required by the import path."""

    code = r"""
import builtins
original_import = builtins.__import__

def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name.split(".", 1)[0] in {
        "redis", "celery", "psycopg", "pgvector", "openai", "anthropic",
        "watchdog", "docx", "numpy",
    }:
        raise ImportError(f"blocked optional dependency: {name}")
    return original_import(name, globals, locals, fromlist, level)

builtins.__import__ = guarded_import
from apps.api.src import main, worker
assert main.app is not None
assert worker.celery_app is not None
assert "kb.index_vault" in worker.celery_app.tasks
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
