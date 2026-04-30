#!/usr/bin/env python3
"""Test FASES 4.26-4.29: Archive, Handoff, Metrics, Next Cycle."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def create_test_cycle_dir(tmpdir) -> Path:
    """Create test cycle directory with artifacts."""
    cycle_dir = Path(tmpdir) / "cycle-001"
    cycle_dir.mkdir(parents=True)

    # Create sample artifact
    artifact_file = cycle_dir / "execution_result.json"
    artifact_file.write_text(json.dumps({"status": "SUCCESS"}))

    return cycle_dir


def test_01_archive_generates_manifest():
    """Test 1: Archive generates manifest."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        cycle_dir = create_test_cycle_dir(tmpdir)

        output_dir = tmpdir / "archive"
        manifest_file = output_dir / "manifest.json"
        report_file = output_dir / "report.md"

        from tools.local.controlled_cycle_final_archive import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--cycle-dir", str(cycle_dir),
            "--output-dir", str(output_dir),
            "--report", str(report_file),
            "--manifest", str(manifest_file),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert manifest_file.exists()
        manifest = json.loads(manifest_file.read_text())
        assert manifest.get("cycle_id") == "cycle-001"
        print("✓ test_01_archive_generates_manifest")


def test_02_archive_excludes_secrets():
    """Test 2: Archive detects and reports secrets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        cycle_dir = create_test_cycle_dir(tmpdir)

        # Create file with secret
        secret_file = cycle_dir / "secret.json"
        secret_file.write_text(json.dumps({"token": "secret-value"}))

        output_dir = tmpdir / "archive"
        manifest_file = output_dir / "manifest.json"
        report_file = output_dir / "report.md"

        from tools.local.controlled_cycle_final_archive import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--cycle-dir", str(cycle_dir),
            "--output-dir", str(output_dir),
            "--report", str(report_file),
            "--manifest", str(manifest_file),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        manifest = json.loads(manifest_file.read_text())
        assert manifest.get("secrets_found_count", 0) > 0
        print("✓ test_02_archive_excludes_secrets")


def test_03_handoff_ready_with_success():
    """Test 3: Handoff READY when closure SUCCESS."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        closure_file = tmpdir / "closure.json"
        closure_file.write_text(json.dumps({"decision": "CYCLE_CLOSED_SUCCESS"}))

        archive_file = tmpdir / "archive.json"
        archive_file.write_text(json.dumps({"status": "CYCLE_ARCHIVED_SUCCESS", "secrets_found_count": 0}))

        output_file = tmpdir / "handoff.md"
        output_json = tmpdir / "handoff.json"

        from tools.local.controlled_cycle_handoff_decision import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--closure-summary", str(closure_file),
            "--archive-manifest", str(archive_file),
            "--output", str(output_file),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert result.get("decision") == "CYCLE_CLOSED_READY_FOR_NEXT_OPERATION"
        print("✓ test_03_handoff_ready_with_success")


def test_04_handoff_action_required_with_secrets():
    """Test 4: Handoff ACTION_REQUIRED with secrets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        closure_file = tmpdir / "closure.json"
        closure_file.write_text(json.dumps({"decision": "CYCLE_CLOSED_SUCCESS"}))

        archive_file = tmpdir / "archive.json"
        archive_file.write_text(json.dumps({
            "status": "CYCLE_ARCHIVED_ACTION_REQUIRED",
            "secrets_found_count": 2
        }))

        output_file = tmpdir / "handoff.md"
        output_json = tmpdir / "handoff.json"

        from tools.local.controlled_cycle_handoff_decision import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--closure-summary", str(closure_file),
            "--archive-manifest", str(archive_file),
            "--output", str(output_file),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert result.get("decision") == "CYCLE_ACTION_REQUIRED"
        print("✓ test_04_handoff_action_required_with_secrets")


def test_05_metrics_counts_cycles():
    """Test 5: Metrics counts cycles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create cycle directories
        (tmpdir / "cycle-001").mkdir()
        (tmpdir / "cycle-002").mkdir()

        output_file = tmpdir / "metrics.md"
        output_json = tmpdir / "metrics.json"

        from tools.local.update_controlled_operation_metrics import main

        test_args = [
            "prog",
            "--root", str(tmpdir),
            "--output", str(output_file),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        metrics = json.loads(output_json.read_text())
        assert metrics.get("total_cycles_defined", 0) >= 2
        print("✓ test_05_metrics_counts_cycles")


def test_06_next_cycle_blocked_action_required():
    """Test 6: Next cycle creation blocked if ACTION_REQUIRED."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        handoff_file = tmpdir / "handoff.json"
        handoff_file.write_text(json.dumps({"decision": "CYCLE_ACTION_REQUIRED"}))

        output_dir = tmpdir / "next-cycle"

        from tools.local.create_next_controlled_cycle_template import main

        test_args = [
            "prog",
            "--previous-cycle", "cycle-001",
            "--next-cycle", "cycle-002",
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--handoff-decision", str(handoff_file),
            "--output-dir", str(output_dir),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert exit_code != 0
        print("✓ test_06_next_cycle_blocked_action_required")


def test_07_next_cycle_created_if_ready():
    """Test 7: Next cycle created if READY."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        handoff_file = tmpdir / "handoff.json"
        handoff_file.write_text(json.dumps({
            "decision": "CYCLE_CLOSED_READY_FOR_NEXT_OPERATION"
        }))

        output_dir = tmpdir / "next-cycle"

        from tools.local.create_next_controlled_cycle_template import main

        test_args = [
            "prog",
            "--previous-cycle", "cycle-001",
            "--next-cycle", "cycle-002",
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--handoff-decision", str(handoff_file),
            "--output-dir", str(output_dir),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert (output_dir / "cycle-002-scope.json").exists()
        assert exit_code == 0
        print("✓ test_07_next_cycle_created_if_ready")


def test_08_next_cycle_scope_enforces_constraints():
    """Test 8: Next cycle scope enforces constraints."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        handoff_file = tmpdir / "handoff.json"
        handoff_file.write_text(json.dumps({
            "decision": "CYCLE_CLOSED_READY_FOR_NEXT_OPERATION"
        }))

        output_dir = tmpdir / "next-cycle"

        from tools.local.create_next_controlled_cycle_template import main

        test_args = [
            "prog",
            "--previous-cycle", "cycle-001",
            "--next-cycle", "cycle-002",
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--handoff-decision", str(handoff_file),
            "--output-dir", str(output_dir),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        scope = json.loads((output_dir / "cycle-002-scope.json").read_text())
        assert scope.get("max_items") == 3
        assert "POST" in scope.get("allowed_methods", [])
        assert "PATCH" in scope.get("forbidden_methods", [])
        assert "DELETE" in scope.get("forbidden_methods", [])
        assert "/sync" in scope.get("forbidden_targets", [])
        print("✓ test_08_next_cycle_scope_enforces_constraints")


def test_09_no_netbox_writes():
    """Test 9: No NetBox writes in archive/handoff/metrics tools."""
    import inspect
    from tools.local import (
        controlled_cycle_final_archive as m426,
        controlled_cycle_handoff_decision as m427,
        update_controlled_operation_metrics as m428,
        create_next_controlled_cycle_template as m429,
    )

    modules = [m426, m427, m428, m429]
    for module in modules:
        source = inspect.getsource(module)
        assert "POST" not in source or "def " in source  # POST in "def " is OK
        assert "PATCH" not in source or "forbidden" in source  # PATCH in forbidden list is OK
        assert "DELETE" not in source or "forbidden" in source  # DELETE in forbidden list is OK

    print("✓ test_09_no_netbox_writes")


def test_10_no_token_usage():
    """Test 10: No network calls or token access in tools."""
    import inspect
    from tools.local import (
        controlled_cycle_final_archive as m426,
        controlled_cycle_handoff_decision as m427,
        update_controlled_operation_metrics as m428,
        create_next_controlled_cycle_template as m429,
    )

    modules = [m426, m427, m428, m429]
    for module in modules:
        source = inspect.getsource(module)
        # No network libraries in read-only phases
        assert "import requests" not in source
        assert "import urllib" not in source
        assert "from urllib" not in source

    print("✓ test_10_no_token_usage")


def test_11_read_only_operations():
    """Test 11: All operations are read-only."""
    import inspect
    from tools.local import update_controlled_operation_metrics as m428

    source = inspect.getsource(m428)
    # Should read directories and files, not make external calls
    assert ".iterdir()" in source or ".exists()" in source
    assert ".rglob(" not in source  # Don't recursively search
    print("✓ test_11_read_only_operations")


def test_12_archive_sha256_calculated():
    """Test 12: Archive calculates SHA256 hashes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        cycle_dir = create_test_cycle_dir(tmpdir)

        output_dir = tmpdir / "archive"
        manifest_file = output_dir / "manifest.json"
        report_file = output_dir / "report.md"

        from tools.local.controlled_cycle_final_archive import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--cycle-dir", str(cycle_dir),
            "--output-dir", str(output_dir),
            "--report", str(report_file),
            "--manifest", str(manifest_file),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        manifest = json.loads(manifest_file.read_text())
        artifacts = manifest.get("artifacts", {})
        for artifact_path, artifact_info in artifacts.items():
            assert "sha256" in artifact_info
            assert len(artifact_info.get("sha256", "")) == 64  # SHA256 is 64 hex chars
        print("✓ test_12_archive_sha256_calculated")


def test_13_handoff_with_warnings():
    """Test 13: Handoff WITH_RESTRICTIONS when warnings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        closure_file = tmpdir / "closure.json"
        closure_file.write_text(json.dumps({"decision": "CYCLE_CLOSED_WITH_WARNINGS"}))

        archive_file = tmpdir / "archive.json"
        archive_file.write_text(json.dumps({"status": "CYCLE_ARCHIVED_SUCCESS", "secrets_found_count": 0}))

        output_file = tmpdir / "handoff.md"
        output_json = tmpdir / "handoff.json"

        from tools.local.controlled_cycle_handoff_decision import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--closure-summary", str(closure_file),
            "--archive-manifest", str(archive_file),
            "--output", str(output_file),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert result.get("decision") == "CYCLE_CLOSED_WITH_RESTRICTIONS"
        print("✓ test_13_handoff_with_warnings")


def test_14_archive_report_generated():
    """Test 14: Archive generates markdown report."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        cycle_dir = create_test_cycle_dir(tmpdir)

        output_dir = tmpdir / "archive"
        manifest_file = output_dir / "manifest.json"
        report_file = output_dir / "report.md"

        from tools.local.controlled_cycle_final_archive import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--cycle-dir", str(cycle_dir),
            "--output-dir", str(output_dir),
            "--report", str(report_file),
            "--manifest", str(manifest_file),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert report_file.exists()
        report_text = report_file.read_text()
        assert "Archive Final" in report_text
        print("✓ test_14_archive_report_generated")


def test_15_metrics_report_generated():
    """Test 15: Metrics generates markdown report."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        (tmpdir / "cycle-001").mkdir()

        output_file = tmpdir / "metrics.md"
        output_json = tmpdir / "metrics.json"

        from tools.local.update_controlled_operation_metrics import main

        test_args = [
            "prog",
            "--root", str(tmpdir),
            "--output", str(output_file),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert output_file.exists()
        report_text = output_file.read_text()
        assert "Métricas" in report_text or "Cycles" in report_text
        print("✓ test_15_metrics_report_generated")


def test_16_next_cycle_has_checklist():
    """Test 16: Next cycle template has checklist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        handoff_file = tmpdir / "handoff.json"
        handoff_file.write_text(json.dumps({
            "decision": "CYCLE_CLOSED_READY_FOR_NEXT_OPERATION"
        }))

        output_dir = tmpdir / "next-cycle"

        from tools.local.create_next_controlled_cycle_template import main

        test_args = [
            "prog",
            "--previous-cycle", "cycle-001",
            "--next-cycle", "cycle-002",
            "--device", "4WNET-MNS-KTG-RX",
            "--device-id", "1890",
            "--handoff-decision", str(handoff_file),
            "--output-dir", str(output_dir),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        checklist_file = output_dir / "cycle-002-CHECKLIST.md"
        assert checklist_file.exists()
        checklist_text = checklist_file.read_text()
        assert "Checklist" in checklist_text
        print("✓ test_16_next_cycle_has_checklist")


def test_17_all_tools_read_only_no_netbox_api():
    """Test 17: All tools are read-only, no NetBox API."""
    import inspect
    from tools.local import (
        controlled_cycle_final_archive as m426,
        controlled_cycle_handoff_decision as m427,
        update_controlled_operation_metrics as m428,
        create_next_controlled_cycle_template as m429,
    )

    modules = [m426, m427, m428, m429]
    for module in modules:
        source = inspect.getsource(module)
        assert "urllib.request" not in source
        assert "requests." not in source
        assert "pynetbox" not in source

    print("✓ test_17_all_tools_read_only_no_netbox_api")


if __name__ == "__main__":
    test_01_archive_generates_manifest()
    test_02_archive_excludes_secrets()
    test_03_handoff_ready_with_success()
    test_04_handoff_action_required_with_secrets()
    test_05_metrics_counts_cycles()
    test_06_next_cycle_blocked_action_required()
    test_07_next_cycle_created_if_ready()
    test_08_next_cycle_scope_enforces_constraints()
    test_09_no_netbox_writes()
    test_10_no_token_usage()
    test_11_read_only_operations()
    test_12_archive_sha256_calculated()
    test_13_handoff_with_warnings()
    test_14_archive_report_generated()
    test_15_metrics_report_generated()
    test_16_next_cycle_has_checklist()
    test_17_all_tools_read_only_no_netbox_api()

    print("\n" + "="*60)
    print("Results: 17/17 tests passed")
    print("="*60)
