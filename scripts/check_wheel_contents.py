"""Verify that the built API wheel is self-contained."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import venv
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_MEMBERS = (
    "apps/api/src/__init__.py",
    "apps/api/src/main.py",
    "apps/api/src/internal/__init__.py",
    "apps/api/src/internal/vendor_core/__init__.py",
    "apps/api/src/internal/vendor_core/config.py",
    "apps/api/src/internal/vendor_core/database.py",
    "apps/api/src/internal/vendor_core/docparse.py",
    "apps/api/src/internal/vendor_core/embeddings.py",
    "apps/api/src/internal/vendor_core/errors.py",
    "apps/api/src/internal/vendor_core/evaljudge.py",
    "apps/api/src/internal/vendor_core/health.py",
    "apps/api/src/internal/vendor_core/llm.py",
    "apps/api/src/internal/vendor_core/logging.py",
    "apps/api/src/internal/vendor_core/pricing.py",
    "apps/api/src/internal/vendor_core/redis.py",
    "apps/api/src/internal/vendor_core/tasks.py",
    "apps/api/src/internal/vendor_core/testing.py",
    "apps/api/src/internal/vendor_core/vectorstore.py",
)
ISOLATED_IMPORTS = (
    "apps.api.src",
    "apps.api.src.main",
    "apps.api.src.config",
    "apps.api.src.db",
    "apps.api.src.models",
    "apps.api.src.indexer",
    "apps.api.src.embeddings",
    "apps.api.src.worker",
    "apps.api.src.internal.vendor_core.config",
    "apps.api.src.internal.vendor_core.database",
    "apps.api.src.internal.vendor_core.docparse",
    "apps.api.src.internal.vendor_core.embeddings",
    "apps.api.src.internal.vendor_core.errors",
    "apps.api.src.internal.vendor_core.evaljudge",
    "apps.api.src.internal.vendor_core.health",
    "apps.api.src.internal.vendor_core.llm",
    "apps.api.src.internal.vendor_core.logging",
    "apps.api.src.internal.vendor_core.pricing",
    "apps.api.src.internal.vendor_core.redis",
    "apps.api.src.internal.vendor_core.tasks",
    "apps.api.src.internal.vendor_core.testing",
    "apps.api.src.internal.vendor_core.vectorstore",
)


def check_wheel(wheel: Path) -> None:
    """Reject incomplete wheels and accidental top-level shared-core packages."""

    with zipfile.ZipFile(wheel) as archive:
        members = set(archive.namelist())
    missing = sorted(set(REQUIRED_MEMBERS) - members)
    external = sorted(name for name in members if name.startswith("shared_core/"))
    if missing or external:
        problems: list[str] = []
        if missing:
            problems.append("missing: " + ", ".join(missing))
        if external:
            problems.append("unexpected external namespace: " + ", ".join(external))
        raise SystemExit("Wheel content check failed: " + "; ".join(problems))


def _venv_python(environment: Path) -> Path:
    if sys.platform == "win32":
        return environment / "Scripts" / "python.exe"
    return environment / "bin" / "python"


def verify_isolated_install(wheel: Path) -> None:
    """Install the wheel in a temporary venv, import it, and run migrations."""

    with tempfile.TemporaryDirectory(prefix="pkb-wheel-check-") as temp_name:
        temp = Path(temp_name)
        environment = temp / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = _venv_python(environment)
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "--disable-pip-version-check",
                "install",
                f"{wheel.resolve()}[dev]",
            ],
            cwd=temp,
            check=True,
            timeout=240,
        )

        modules = repr(ISOLATED_IMPORTS)
        probe = f"""
import importlib
import sys
from pathlib import Path

external = "shared" + "_core"
for name in {modules}:
    module = importlib.import_module(name)
    if name == "apps.api.src":
        package_path = Path(module.__file__).resolve()
        expected_root = Path({str(environment)!r}).resolve()
        assert package_path.is_relative_to(expected_root), package_path
assert external not in sys.modules
assert importlib.util.find_spec(external) is None
"""
        subprocess.run(
            [str(python), "-c", probe],
            cwd=temp,
            check=True,
            timeout=60,
        )

        migration_database = temp / "migration.db"
        migration_env = dict(os.environ)
        migration_env["DATABASE_URL"] = f"sqlite:///{migration_database.as_posix()}"
        subprocess.run(
            [
                str(python),
                "-m",
                "alembic",
                "-c",
                str(ROOT / "alembic.ini"),
                "upgrade",
                "head",
            ],
            cwd=temp,
            env=migration_env,
            check=True,
            timeout=60,
        )
        if not migration_database.exists():
            raise SystemExit("Isolated migration did not create its SQLite database.")


def main() -> None:
    wheels = sorted(
        (ROOT / "dist").glob("*.whl"), key=lambda path: path.stat().st_mtime
    )
    if not wheels:
        raise SystemExit("No wheel found under dist/. Run 'python -m build' first.")
    wheel = wheels[-1]
    check_wheel(wheel)
    verify_isolated_install(wheel)
    print(f"Wheel content and isolated import checks passed: {wheel.name}")


if __name__ == "__main__":
    sys.exit(main())
