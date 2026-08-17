"""Reject external shared-core dependencies and credential-shaped secrets."""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".cfg",
    ".cjs",
    ".env",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".ps1",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
TEXT_NAMES = {"Dockerfile", "Makefile"}
FORBIDDEN_ENV_NAMES = {".env", ".env.local", ".env.production"}


@dataclass(frozen=True)
class Rule:
    label: str
    pattern: re.Pattern[str]


RULES = (
    Rule(
        "external shared-core import",
        re.compile(
            r"(?m)^\s*(?:from\s+shared_core(?:\.|\s)|"
            r"import\s+shared_core(?:\.|\s|$))"
        ),
    ),
    Rule(
        "Git-installed shared-core dependency",
        re.compile(
            r"git\+https?://[^\s\"'#]*(?:operator-shared-core|shared-core)",
            re.IGNORECASE,
        ),
    ),
    Rule(
        "sibling shared-core dependency",
        re.compile(r"(?:\.\.[\\/])+(?:operator-)?shared-core", re.IGNORECASE),
    ),
    Rule(
        "GitHub personal access token",
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    ),
    Rule(
        "OpenAI API key",
        re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    ),
    Rule("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    Rule(
        "private key material",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
)


def _git_files(root: Path) -> list[Path] | None:
    top_level = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if top_level.returncode != 0:
        return None
    try:
        git_root = Path(top_level.stdout.strip()).resolve()
    except OSError:
        return None
    if git_root != root:
        return None
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return [root / name.decode("utf-8") for name in result.stdout.split(b"\0") if name]


def _candidate_files(root: Path) -> Iterable[Path]:
    paths = _git_files(root)
    if paths is None:
        paths = list(root.rglob("*"))
    for path in paths:
        if not path.is_file():
            continue
        if path.name in TEXT_NAMES or path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def find_violations(root: Path) -> list[tuple[str, str, int]]:
    """Return sorted ``(path, rule, line)`` violations without secret values."""

    violations: list[tuple[str, str, int]] = []
    for path in _candidate_files(root):
        relative = path.relative_to(root).as_posix()
        if path.name in FORBIDDEN_ENV_NAMES:
            violations.append((relative, "committed environment file", 1))
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for rule in RULES:
            for match in rule.pattern.finditer(content):
                line = content.count("\n", 0, match.start()) + 1
                violations.append((relative, rule.label, line))
    return sorted(set(violations))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    violations = find_violations(root)
    if violations:
        print("Forbidden dependency or secret scan failed:")
        for relative, label, line in violations:
            print(f"- {relative}:{line}: {label}")
        return 1
    print("No forbidden dependencies or committed secrets found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
