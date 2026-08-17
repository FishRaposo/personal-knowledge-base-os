"""Verify that the built API wheel is self-contained."""

from __future__ import annotations

import sys
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


def main() -> None:
    wheels = sorted(
        (ROOT / "dist").glob("*.whl"), key=lambda path: path.stat().st_mtime
    )
    if not wheels:
        raise SystemExit("No wheel found under dist/. Run 'python -m build' first.")
    wheel = wheels[-1]
    check_wheel(wheel)
    print(f"Wheel content check passed: {wheel.name}")


if __name__ == "__main__":
    sys.exit(main())
