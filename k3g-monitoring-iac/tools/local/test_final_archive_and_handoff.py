#!/usr/bin/env python3
"""Test FASES 2.57-2.58: Pilot archive and operational handoff.

15 test cases covering:
- Archive creation and manifest generation
- Hash computation
- Secret exclusion
- Handoff decision logic
- Safety confirmations
- No token exposure
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def create_mock_reports_structure(tmpdir: Path) -> Path:
    """Create mock reports directory structure."""
    reports_root = Path(tmpdir) / "reports"
    reports_root.mkdir()

    # Create phase directories with mock artifacts
    phases = {
        "week1": [
            ("week1-responses.json", '{"status": "collected"}'),
            ("week1-summary.md", "# Week 1 Summary"),
        ],
        "week2-review": [
            ("week2-review.json", '{"status": "reviewed"}'),
            ("week2-summary.md", "# Week 2 Summary"),
        ],
        "approval": [
            ("approval-123.json", '{"approval_id": "123", "status": "approved"}'),
        ],
        "apply-plans": [
            ("apply-plan.json", '{"apply_plan_id": "plan-1"}'),
        ],
        "dryrun-simulation": [
            ("simulation.json", '{"simulation_id": "sim-1", "status": "PASSED"}'),
        ],
        "real-write-execution": [
            ("execution-result.json", '{"execution_id": "exec-1", "status": "SUCCESS"}'),
            ("execution-result.md", "# Execution Result"),
        ],
        "closure": [
            ("closure-package.json", '{"closure_decision": "SUCCESS"}'),
        ],
    }

    for phase, files in phases.items():
        phase_dir = reports_root / phase
        phase_dir.mkdir()
        for filename, content in files:
            (phase_dir / filename).write_text(content)

    return reports_root


def test_01_archive_creates_manifest():
    """Test 1: Archive creates manifest JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reports_root = create_mock_reports_structure(tmpdir)
        output_dir = Path(tmpdir) / "archive"
        report_file = output_dir / "ARCHIVE.md"

        from tools.local.build_pilot_final_archive import main

        test_args = [
            "prog",
            "--device",
            "test-device",
            "--device-id",
            "123",
            "--reports-root",
            str(reports_root),
            "--output-dir",
            str(output_dir),
            "--report",
            str(report_file),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert exit_code == 0
        manifest_file = output_dir / "pilot-final-manifest.json"
        assert manifest_file.exists()

        manifest = json.loads(manifest_file.read_text())
        assert manifest["device"] == "test-device"
        assert manifest["device_id"] == "123"


def test_02_archive_computes_hashes():
    """Test 2: Archive computes SHA256 hashes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reports_root = create_mock_reports_structure(tmpdir)
        output_dir = Path(tmpdir) / "archive"
        report_file = output_dir / "ARCHIVE.md"

        from tools.local.build_pilot_final_archive import main

        test_args = [
            "prog",
            "--device",
            "test",
            "--device-id",
            "1",
            "--reports-root",
            str(reports_root),
            "--output-dir",
            str(output_dir),
            "--report",
            str(report_file),
        ]

        with patch("sys.argv", test_args):
            main()

        manifest = json.loads((output_dir / "pilot-final-manifest.json").read_text())
        artifacts = manifest["artifacts"]

        # All artifacts should have sha256
        for artifact in artifacts:
            assert "sha256" in artifact
            assert len(artifact["sha256"]) == 64  # SHA256 is 64 hex chars


def test_03_archive_excludes_secrets():
    """Test 3: Archive excludes files with secrets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reports_root = create_mock_reports_structure(tmpdir)

        # Add file with secret
        secret_file = reports_root / "secret" / "with-token.json"
        secret_file.parent.mkdir()
        secret_file.write_text('{"token": "secret123"}')

        output_dir = Path(tmpdir) / "archive"
        report_file = output_dir / "ARCHIVE.md"

        from tools.local.build_pilot_final_archive import main

        test_args = [
            "prog",
            "--device",
            "test",
            "--device-id",
            "1",
            "--reports-root",
            str(reports_root),
            "--output-dir",
            str(output_dir),
            "--report",
            str(report_file),
        ]

        with patch("sys.argv", test_args):
            main()

        manifest = json.loads((output_dir / "pilot-final-manifest.json").read_text())
        files = [a["file"] for a in manifest["artifacts"]]

        # Secret file should not be in archive
        assert not any("with-token" in f for f in files)


def test_04_archive_excludes_env():
    """Test 4: Archive excludes .env files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reports_root = create_mock_reports_structure(tmpdir)

        # Add .env file
        env_file = reports_root / "config" / ".env"
        env_file.parent.mkdir()
        env_file.write_text("NETBOX_TOKEN=secret")

        output_dir = Path(tmpdir) / "archive"
        report_file = output_dir / "ARCHIVE.md"

        from tools.local.build_pilot_final_archive import main

        test_args = [
            "prog",
            "--device",
            "test",
            "--device-id",
            "1",
            "--reports-root",
            str(reports_root),
            "--output-dir",
            str(output_dir),
            "--report",
            str(report_file),
        ]

        with patch("sys.argv", test_args):
            main()

        manifest = json.loads((output_dir / "pilot-final-manifest.json").read_text())
        files = [a["file"] for a in manifest["artifacts"]]

        # .env should not be in archive
        assert not any(".env" in f for f in files)


def test_05_archive_safety_confirmations():
    """Test 5: Archive includes safety confirmations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reports_root = create_mock_reports_structure(tmpdir)
        output_dir = Path(tmpdir) / "archive"
        report_file = output_dir / "ARCHIVE.md"

        from tools.local.build_pilot_final_archive import main

        test_args = [
            "prog",
            "--device",
            "test",
            "--device-id",
            "1",
            "--reports-root",
            str(reports_root),
            "--output-dir",
            str(output_dir),
            "--report",
            str(report_file),
        ]

        with patch("sys.argv", test_args):
            main()

        manifest = json.loads((output_dir / "pilot-final-manifest.json").read_text())
        safety = manifest["safety_confirmations"]

        assert safety["no_tokens"] is True
        assert safety["no_env_files"] is True
        assert safety["no_secrets"] is True
        assert safety["hashes_verified"] is True


def test_06_archive_generates_markdown():
    """Test 6: Archive generates markdown report."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reports_root = create_mock_reports_structure(tmpdir)
        output_dir = Path(tmpdir) / "archive"
        report_file = output_dir / "ARCHIVE.md"

        from tools.local.build_pilot_final_archive import main

        test_args = [
            "prog",
            "--device",
            "test-device",
            "--device-id",
            "123",
            "--reports-root",
            str(reports_root),
            "--output-dir",
            str(output_dir),
            "--report",
            str(report_file),
        ]

        with patch("sys.argv", test_args):
            main()

        assert report_file.exists()
        content = report_file.read_text()

        assert "Arquivo Final do Piloto" in content
        assert "test-device" in content
        assert "PILOT_ARCHIVED_SUCCESS" in content


def test_07_handoff_ready_when_all_ok():
    """Test 7: Handoff decision READY when all phases OK."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        archive_manifest = {
            "final_decision": "PILOT_ARCHIVED_SUCCESS",
            "total_artifacts": 10,
            "safety_confirmations": {
                "no_tokens": True,
                "no_secrets": True,
            },
            "artifacts": [
                {
                    "file": "verification-result.json",
                    "phase": "Verification",
                },
                {
                    "file": "compliance-result.json",
                    "phase": "Compliance",
                },
            ],
        }

        closure_summary = {
            "closure_decision": "WRITE_EXECUTION_COMPLETE_SUCCESS",
            "token_logged": False,
        }

        manifest_file = tmpdir / "manifest.json"
        manifest_file.write_text(json.dumps(archive_manifest))

        closure_file = tmpdir / "closure.json"
        closure_file.write_text(json.dumps(closure_summary))

        output_file = tmpdir / "decision.md"
        output_json = tmpdir / "decision.json"

        from tools.local.build_operational_handoff_decision import main

        test_args = [
            "prog",
            "--device",
            "test",
            "--device-id",
            "1",
            "--archive-manifest",
            str(manifest_file),
            "--closure-summary",
            str(closure_file),
            "--output",
            str(output_file),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        decision_json = json.loads(output_json.read_text())
        assert decision_json["decision"] == "READY_FOR_CONTROLLED_OPERATION"


def test_08_handoff_not_ready_when_archive_has_secrets():
    """Test 8: Handoff NOT_READY when archive safety flags false."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Archive with safety issue
        archive_manifest = {
            "final_decision": "PILOT_ARCHIVED_SUCCESS",
            "total_artifacts": 10,
            "safety_confirmations": {
                "no_tokens": False,  # ISSUE
                "no_secrets": True,
            },
            "artifacts": [
                {"file": "verification-result.json", "phase": "Verification"},
                {"file": "compliance-result.json", "phase": "Compliance"},
            ],
        }

        closure_summary = {
            "closure_decision": "WRITE_EXECUTION_COMPLETE_SUCCESS",
            "token_logged": False,
        }

        manifest_file = tmpdir / "manifest.json"
        manifest_file.write_text(json.dumps(archive_manifest))

        closure_file = tmpdir / "closure.json"
        closure_file.write_text(json.dumps(closure_summary))

        output_file = tmpdir / "decision.md"
        output_json = tmpdir / "decision.json"

        from tools.local.build_operational_handoff_decision import main

        test_args = [
            "prog",
            "--device",
            "test",
            "--device-id",
            "1",
            "--archive-manifest",
            str(manifest_file),
            "--closure-summary",
            str(closure_file),
            "--output",
            str(output_file),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            main()

        decision_json = json.loads(output_json.read_text())
        assert decision_json["decision"] == "NOT_READY_FOR_OPERATION"


def test_09_handoff_not_ready_when_closure_failed():
    """Test 9: Handoff decision NOT_READY when closure failed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        archive_manifest = {
            "final_decision": "PILOT_ARCHIVED_SUCCESS",
            "total_artifacts": 10,
            "safety_confirmations": {
                "no_tokens": True,
                "no_secrets": True,
            },
            "artifacts": [{"file": "verification-result.json", "phase": "Verification"}],
        }

        # Closure failed
        closure_summary = {
            "closure_decision": "WRITE_EXECUTION_FAILED",
            "token_logged": False,
        }

        manifest_file = tmpdir / "manifest.json"
        manifest_file.write_text(json.dumps(archive_manifest))

        closure_file = tmpdir / "closure.json"
        closure_file.write_text(json.dumps(closure_summary))

        output_file = tmpdir / "decision.md"
        output_json = tmpdir / "decision.json"

        from tools.local.build_operational_handoff_decision import main

        test_args = [
            "prog",
            "--device",
            "test",
            "--device-id",
            "1",
            "--archive-manifest",
            str(manifest_file),
            "--closure-summary",
            str(closure_file),
            "--output",
            str(output_file),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        decision_json = json.loads(output_json.read_text())
        assert decision_json["decision"] == "NOT_READY_FOR_OPERATION"


def test_10_handoff_not_ready_when_no_verification():
    """Test 10: Handoff NOT_READY when verification artifacts missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Archive without verification
        archive_manifest = {
            "final_decision": "PILOT_ARCHIVED_SUCCESS",
            "total_artifacts": 5,
            "safety_confirmations": {
                "no_tokens": True,
                "no_secrets": True,
            },
            "artifacts": [
                {"file": "execution-result.json", "phase": "Execution"},
            ],
        }

        closure_summary = {
            "closure_decision": "WRITE_EXECUTION_COMPLETE_SUCCESS",
            "token_logged": False,
        }

        manifest_file = tmpdir / "manifest.json"
        manifest_file.write_text(json.dumps(archive_manifest))

        closure_file = tmpdir / "closure.json"
        closure_file.write_text(json.dumps(closure_summary))

        output_file = tmpdir / "decision.md"
        output_json = tmpdir / "decision.json"

        from tools.local.build_operational_handoff_decision import main

        test_args = [
            "prog",
            "--device",
            "test",
            "--device-id",
            "1",
            "--archive-manifest",
            str(manifest_file),
            "--closure-summary",
            str(closure_file),
            "--output",
            str(output_file),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            main()

        decision_json = json.loads(output_json.read_text())
        assert decision_json["decision"] == "NOT_READY_FOR_OPERATION"


def test_11_handoff_generates_markdown():
    """Test 11: Handoff generates markdown decision."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        archive_manifest = {
            "final_decision": "PILOT_ARCHIVED_SUCCESS",
            "total_artifacts": 10,
            "safety_confirmations": {
                "no_tokens": True,
                "no_secrets": True,
            },
            "artifacts": [
                {"file": "verification-result.json", "phase": "Verification"},
                {"file": "compliance-result.json", "phase": "Compliance"},
            ],
        }

        closure_summary = {
            "closure_decision": "WRITE_EXECUTION_COMPLETE_SUCCESS",
            "token_logged": False,
        }

        manifest_file = tmpdir / "manifest.json"
        manifest_file.write_text(json.dumps(archive_manifest))

        closure_file = tmpdir / "closure.json"
        closure_file.write_text(json.dumps(closure_summary))

        output_file = tmpdir / "decision.md"
        output_json = tmpdir / "decision.json"

        from tools.local.build_operational_handoff_decision import main

        test_args = [
            "prog",
            "--device",
            "test-device",
            "--device-id",
            "123",
            "--archive-manifest",
            str(manifest_file),
            "--closure-summary",
            str(closure_file),
            "--output",
            str(output_file),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            main()

        assert output_file.exists()
        content = output_file.read_text()

        assert "Decisão de Handoff Operacional" in content
        assert "test-device" in content
        assert "READY_FOR_CONTROLLED_OPERATION" in content


def test_12_handoff_safety_confirmations():
    """Test 12: Handoff includes safety confirmations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        archive_manifest = {
            "final_decision": "PILOT_ARCHIVED_SUCCESS",
            "total_artifacts": 10,
            "safety_confirmations": {
                "no_tokens": True,
                "no_secrets": True,
            },
            "artifacts": [
                {"file": "verification-result.json", "phase": "Verification"},
                {"file": "compliance-result.json", "phase": "Compliance"},
            ],
        }

        closure_summary = {
            "closure_decision": "WRITE_EXECUTION_COMPLETE_SUCCESS",
            "token_logged": False,
        }

        manifest_file = tmpdir / "manifest.json"
        manifest_file.write_text(json.dumps(archive_manifest))

        closure_file = tmpdir / "closure.json"
        closure_file.write_text(json.dumps(closure_summary))

        output_file = tmpdir / "decision.md"
        output_json = tmpdir / "decision.json"

        from tools.local.build_operational_handoff_decision import main

        test_args = [
            "prog",
            "--device",
            "test",
            "--device-id",
            "1",
            "--archive-manifest",
            str(manifest_file),
            "--closure-summary",
            str(closure_file),
            "--output",
            str(output_file),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            main()

        decision_json = json.loads(output_json.read_text())
        safety = decision_json["safety_confirmations"]

        assert safety["no_tokens"] is True
        assert safety["no_secrets"] is True
        assert safety["audit_trail_complete"] is True


def test_13_archive_no_raw_files():
    """Test 13: Archive excludes raw files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reports_root = create_mock_reports_structure(tmpdir)

        # Add raw file
        raw_file = reports_root / "raw-data" / "raw-output.json"
        raw_file.parent.mkdir()
        raw_file.write_text('{"raw": "data"}')

        output_dir = Path(tmpdir) / "archive"
        report_file = output_dir / "ARCHIVE.md"

        from tools.local.build_pilot_final_archive import main

        test_args = [
            "prog",
            "--device",
            "test",
            "--device-id",
            "1",
            "--reports-root",
            str(reports_root),
            "--output-dir",
            str(output_dir),
            "--report",
            str(report_file),
        ]

        with patch("sys.argv", test_args):
            main()

        manifest = json.loads((output_dir / "pilot-final-manifest.json").read_text())
        files = [a["file"] for a in manifest["artifacts"]]

        # Raw file should not be in archive
        assert not any("raw" in f.lower() for f in files)


def test_14_archive_counts_artifacts():
    """Test 14: Archive counts artifacts correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reports_root = create_mock_reports_structure(tmpdir)
        output_dir = Path(tmpdir) / "archive"
        report_file = output_dir / "ARCHIVE.md"

        from tools.local.build_pilot_final_archive import main

        test_args = [
            "prog",
            "--device",
            "test",
            "--device-id",
            "1",
            "--reports-root",
            str(reports_root),
            "--output-dir",
            str(output_dir),
            "--report",
            str(report_file),
        ]

        with patch("sys.argv", test_args):
            main()

        manifest = json.loads((output_dir / "pilot-final-manifest.json").read_text())
        total = manifest["total_artifacts"]
        artifacts = manifest["artifacts"]

        assert total == len(artifacts)
        assert total > 0


def test_15_handoff_includes_restrictions():
    """Test 15: Handoff markdown includes restrictions section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        archive_manifest = {
            "final_decision": "PILOT_ARCHIVED_SUCCESS",
            "total_artifacts": 10,
            "safety_confirmations": {
                "no_tokens": True,
                "no_secrets": True,
            },
            "artifacts": [
                {"file": "verification-result.json", "phase": "Verification"},
                {"file": "compliance-result.json", "phase": "Compliance"},
            ],
        }

        closure_summary = {
            "closure_decision": "WRITE_EXECUTION_COMPLETE_SUCCESS",
            "token_logged": False,
        }

        manifest_file = tmpdir / "manifest.json"
        manifest_file.write_text(json.dumps(archive_manifest))

        closure_file = tmpdir / "closure.json"
        closure_file.write_text(json.dumps(closure_summary))

        output_file = tmpdir / "decision.md"
        output_json = tmpdir / "decision.json"

        from tools.local.build_operational_handoff_decision import main

        test_args = [
            "prog",
            "--device",
            "test",
            "--device-id",
            "1",
            "--archive-manifest",
            str(manifest_file),
            "--closure-summary",
            str(closure_file),
            "--output",
            str(output_file),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            main()

        content = output_file.read_text()

        # Should have operational rules section
        assert "Regras para Operação Controlada" in content or "Restrições" in content


def main():
    """Run all tests."""
    test_functions = [
        test_01_archive_creates_manifest,
        test_02_archive_computes_hashes,
        test_03_archive_excludes_secrets,
        test_04_archive_excludes_env,
        test_05_archive_safety_confirmations,
        test_06_archive_generates_markdown,
        test_07_handoff_ready_when_all_ok,
        test_08_handoff_not_ready_when_archive_has_secrets,
        test_09_handoff_not_ready_when_closure_failed,
        test_10_handoff_not_ready_when_no_verification,
        test_11_handoff_generates_markdown,
        test_12_handoff_safety_confirmations,
        test_13_archive_no_raw_files,
        test_14_archive_counts_artifacts,
        test_15_handoff_includes_restrictions,
    ]

    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            test_func()
            print(f"✓ {test_func.__name__}")
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
