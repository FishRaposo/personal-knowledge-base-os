"""Release contracts for deterministic offline portfolio evidence."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import portfolio_demo, verify_portfolio_evidence

ROOT = Path(__file__).resolve().parents[1]


def test_evidence_entrypoints_exist() -> None:
    assert (ROOT / "scripts" / "portfolio_demo.py").is_file()
    assert (ROOT / "scripts" / "verify_portfolio_evidence.py").is_file()


def test_offline_bundle_covers_the_approved_product_proof(tmp_path: Path) -> None:
    bundle = tmp_path / "evidence"

    manifest = portfolio_demo.generate_bundle(bundle)
    verified_hash = verify_portfolio_evidence.verify_bundle(bundle)
    report = json.loads((bundle / "report.json").read_text(encoding="utf-8"))

    assert verified_hash == manifest["reproducibility_hash"]
    assert set(report["capabilities"]) == {
        "editing_incremental",
        "frontend_fixtures",
        "ingestion_graph",
        "multi_vault",
        "optional_fallbacks",
        "persistence",
        "retrieval_chat",
        "saved_searches",
        "watcher_events",
        "flashcards",
    }
    assert all(report["assertions"].values())
    assert report["capabilities"]["ingestion_graph"]["dangling_links"]
    assert report["capabilities"]["retrieval_chat"]["chat"]["grounded"] is True
    assert report["capabilities"]["multi_vault"]["isolated"] is True
    assert report["capabilities"]["editing_incremental"]["safe_refusal"] is True
    assert report["capabilities"]["watcher_events"]["sse_replay"] is True
    assert report["capabilities"]["flashcards"]["stable"] is True
    assert report["capabilities"]["persistence"] == {
        "in_memory": {"default_notes": 3, "work_notes": 1},
        "sqlite": {"default_notes": 1, "work_notes": 1},
    }
    assert report["capabilities"]["optional_fallbacks"]["network_required"] is False
    assert report["capabilities"]["frontend_fixtures"]["offline_demo"] is True


def test_two_clean_runs_are_byte_identical(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"

    first_manifest = portfolio_demo.generate_bundle(first)
    second_manifest = portfolio_demo.generate_bundle(second)

    assert (
        first_manifest["reproducibility_hash"]
        == second_manifest["reproducibility_hash"]
    )
    assert {path.name: path.read_bytes() for path in first.iterdir()} == {
        path.name: path.read_bytes() for path in second.iterdir()
    }


def test_documented_script_commands_run_from_the_repository_root(
    tmp_path: Path,
) -> None:
    bundle = tmp_path / "cli-evidence"
    generated = subprocess.run(
        [
            sys.executable,
            "scripts/portfolio_demo.py",
            "--output",
            str(bundle),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert generated.returncode == 0, generated.stderr
    verified = subprocess.run(
        [sys.executable, "scripts/verify_portfolio_evidence.py", str(bundle)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert verified.returncode == 0, verified.stderr


def test_bundle_is_canonical_and_matches_the_tracked_golden(tmp_path: Path) -> None:
    bundle = tmp_path / "evidence"
    portfolio_demo.generate_bundle(bundle)

    report_bytes = (bundle / "report.json").read_bytes()
    golden_bytes = (
        ROOT / "tests" / "fixtures" / "golden" / "portfolio-evidence.json"
    ).read_bytes()

    assert report_bytes == golden_bytes
    assert report_bytes == portfolio_demo.canonical_bytes(json.loads(report_bytes))
    assert {path.name for path in bundle.iterdir()} == {
        "checksums.sha256",
        "manifest.json",
        "report.json",
        "report.md",
    }


def test_make_and_ignore_contracts_are_wired() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "evidence:" in makefile
    assert "python scripts/portfolio_demo.py" in makefile
    assert "python scripts/verify_portfolio_evidence.py" in makefile
    assert "artifacts/portfolio/" in gitignore


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    target = tmp_path / "evidence"
    portfolio_demo.generate_bundle(target)
    return target


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("missing", "missing"),
        ("extra", "unexpected"),
        ("malformed", "malformed"),
        ("tampered", "checksum"),
        ("noncanonical", "canonical"),
        ("checksum", "checksum"),
    ],
)
def test_verifier_rejects_structural_and_checksum_tampering(
    bundle: Path, mutation: str, match: str
) -> None:
    if mutation == "missing":
        (bundle / "report.md").unlink()
    elif mutation == "extra":
        (bundle / "extra.txt").write_text("unexpected", encoding="utf-8")
    elif mutation == "malformed":
        (bundle / "report.json").write_text("{not-json", encoding="utf-8")
    elif mutation == "tampered":
        (bundle / "report.md").write_text("tampered\n", encoding="utf-8")
    elif mutation == "noncanonical":
        report = json.loads((bundle / "report.json").read_text(encoding="utf-8"))
        (bundle / "report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
    elif mutation == "checksum":
        lines = (bundle / "checksums.sha256").read_text(encoding="utf-8").splitlines()
        lines[0] = f"{'0' * 64}  manifest.json"
        (bundle / "checksums.sha256").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

    with pytest.raises(
        verify_portfolio_evidence.EvidenceVerificationError, match=match
    ):
        verify_portfolio_evidence.verify_bundle(bundle)


@pytest.mark.parametrize(
    ("mutation", "value"),
    [
        ("files", None),
        ("file_hash", None),
        ("reproducibility_hash", None),
    ],
)
def test_verifier_rejects_canonical_manifest_type_errors_cleanly(
    bundle: Path, mutation: str, value: object
) -> None:
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    if mutation == "file_hash":
        manifest["files"]["report.json"] = value
    else:
        manifest[mutation] = value
    (bundle / "manifest.json").write_bytes(portfolio_demo.canonical_bytes(manifest))

    with pytest.raises(
        verify_portfolio_evidence.EvidenceVerificationError,
        match="malformed manifest",
    ):
        verify_portfolio_evidence.verify_bundle(bundle)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("assertions", None),
        ("capabilities", None),
        ("reproducibility_hash", None),
        ("schema_version", 1),
    ],
)
def test_verifier_rejects_canonical_report_type_errors_cleanly(
    bundle: Path, field: str, value: object
) -> None:
    report = json.loads((bundle / "report.json").read_text(encoding="utf-8"))
    report[field] = value
    (bundle / "report.json").write_bytes(portfolio_demo.canonical_bytes(report))

    with pytest.raises(
        verify_portfolio_evidence.EvidenceVerificationError,
        match="malformed report",
    ):
        verify_portfolio_evidence.verify_bundle(bundle)


def test_verifier_cli_reports_schema_failure_without_a_traceback(bundle: Path) -> None:
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"] = None
    (bundle / "manifest.json").write_bytes(portfolio_demo.canonical_bytes(manifest))

    result = subprocess.run(
        [sys.executable, "scripts/verify_portfolio_evidence.py", str(bundle)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 1
    assert "malformed manifest" in result.stderr
    assert "Traceback" not in result.stderr


def test_verifier_rejects_self_consistent_semantic_tampering(
    bundle: Path, tmp_path: Path
) -> None:
    report = json.loads((bundle / "report.json").read_text(encoding="utf-8"))
    report["capabilities"]["multi_vault"]["isolated"] = False
    tampered = tmp_path / "self-consistent"
    portfolio_demo.write_bundle(report, tampered)

    with pytest.raises(
        verify_portfolio_evidence.EvidenceVerificationError, match="golden"
    ):
        verify_portfolio_evidence.verify_bundle(tampered)


def test_verifier_does_not_modify_the_bundle(bundle: Path, tmp_path: Path) -> None:
    before = tmp_path / "before"
    shutil.copytree(bundle, before)

    verify_portfolio_evidence.verify_bundle(bundle)

    assert {path.name: path.read_bytes() for path in before.iterdir()} == {
        path.name: path.read_bytes() for path in bundle.iterdir()
    }
