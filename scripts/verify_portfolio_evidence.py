"""Strictly verify a Personal Knowledge Base OS evidence bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from scripts import portfolio_demo
except ModuleNotFoundError:  # direct ``python scripts/...`` execution
    import portfolio_demo  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "fixtures" / "golden" / "portfolio-evidence.json"


class EvidenceVerificationError(ValueError):
    """An evidence bundle is incomplete, noncanonical, or untrusted."""


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    try:
        parsed = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceVerificationError(f"malformed {label}") from exc
    if not isinstance(parsed, dict):
        raise EvidenceVerificationError(f"malformed {label}: object required")
    try:
        canonical = portfolio_demo.canonical_bytes(parsed)
    except (TypeError, ValueError) as exc:
        raise EvidenceVerificationError(f"malformed {label}") from exc
    if raw != canonical:
        raise EvidenceVerificationError(f"canonical JSON required for {label}")
    return parsed, raw


def _validate_shape(report: dict[str, Any], manifest: dict[str, Any]) -> None:
    if set(manifest) != {
        "files",
        "format_version",
        "project",
        "reproducibility_hash",
    }:
        raise EvidenceVerificationError("malformed manifest schema")
    if manifest["format_version"] != portfolio_demo.FORMAT_VERSION:
        raise EvidenceVerificationError("malformed manifest format_version")
    if manifest["project"] != "personal-knowledge-base-os":
        raise EvidenceVerificationError("malformed manifest project")
    if set(manifest["files"]) != {"report.json", "report.md"}:
        raise EvidenceVerificationError("malformed manifest files")
    if set(report) != {
        "assertions",
        "capabilities",
        "mode",
        "project",
        "reproducibility_hash",
        "schema_version",
    }:
        raise EvidenceVerificationError("malformed report schema")
    if (
        report["schema_version"] != "1.0"
        or report["project"] != "personal-knowledge-base-os"
        or report["mode"] != "offline"
        or not isinstance(report["capabilities"], dict)
        or not isinstance(report["assertions"], dict)
        or not report["assertions"]
        or not all(value is True for value in report["assertions"].values())
    ):
        raise EvidenceVerificationError("malformed report semantics")


def _validate_checksums(bundle: Path, expected: dict[str, bytes]) -> None:
    checksum_bytes = (bundle / "checksums.sha256").read_bytes()
    try:
        checksum_text = checksum_bytes.decode("ascii")
    except UnicodeDecodeError as exc:
        raise EvidenceVerificationError("malformed checksum file") from exc
    wanted = "".join(
        f"{_sha256(expected[name])}  {name}\n" for name in sorted(expected)
    )
    if checksum_text != wanted:
        raise EvidenceVerificationError("checksum mismatch: checksums.sha256")


def _read_bundle(
    bundle: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, bytes]]:
    if not bundle.is_dir():
        raise EvidenceVerificationError("missing evidence bundle")
    actual = {path.name for path in bundle.iterdir()}
    missing = portfolio_demo.BUNDLE_FILES - actual
    extra = actual - portfolio_demo.BUNDLE_FILES
    if missing:
        raise EvidenceVerificationError(f"missing evidence file: {sorted(missing)[0]}")
    if extra:
        raise EvidenceVerificationError(f"unexpected evidence file: {sorted(extra)[0]}")

    manifest, manifest_raw = _read_json(bundle / "manifest.json", "manifest")
    report, report_raw = _read_json(bundle / "report.json", "report")
    _validate_shape(report, manifest)
    report_md = (bundle / "report.md").read_bytes()
    expected_payloads = {
        "manifest.json": manifest_raw,
        "report.json": report_raw,
        "report.md": report_md,
    }
    _validate_checksums(bundle, expected_payloads)
    return manifest, report, expected_payloads


def _validate_payloads(
    manifest: dict[str, Any], report: dict[str, Any], payloads: dict[str, bytes]
) -> str:
    for name in ("report.json", "report.md"):
        expected_hash = manifest["files"].get(name)
        if expected_hash != _sha256(payloads[name]):
            raise EvidenceVerificationError(f"checksum mismatch: {name}")

    without_hash = dict(report)
    reproducibility_hash = without_hash.pop("reproducibility_hash", None)
    if not isinstance(reproducibility_hash, str) or len(reproducibility_hash) != 64:
        raise EvidenceVerificationError("malformed reproducibility hash")
    if _sha256(portfolio_demo.canonical_bytes(without_hash)) != reproducibility_hash:
        raise EvidenceVerificationError("checksum mismatch: reproducibility hash")
    if manifest["reproducibility_hash"] != reproducibility_hash:
        raise EvidenceVerificationError("checksum mismatch: manifest hash")
    expected_markdown = portfolio_demo.render_markdown(report).encode("utf-8")
    if payloads["report.md"] != expected_markdown:
        raise EvidenceVerificationError("checksum mismatch: semantic report")
    if not GOLDEN.is_file():
        raise EvidenceVerificationError("missing tracked golden fixture")
    if payloads["report.json"] != GOLDEN.read_bytes():
        raise EvidenceVerificationError("golden evidence mismatch")
    return reproducibility_hash


def verify_bundle(bundle_dir: Path | str = portfolio_demo.DEFAULT_OUTPUT) -> str:
    bundle = Path(bundle_dir)
    manifest, report, payloads = _read_bundle(bundle)
    return _validate_payloads(manifest, report, payloads)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bundle", nargs="?", type=Path, default=portfolio_demo.DEFAULT_OUTPUT
    )
    args = parser.parse_args()
    print(verify_bundle(args.bundle))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
