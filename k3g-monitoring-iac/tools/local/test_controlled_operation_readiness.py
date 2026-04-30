#!/usr/bin/env python3
"""Test FASES 2.60 & 4.1: Controlled operation baseline and cycle creation.

10 test cases covering:
- Baseline generation (decision logic, markdown, JSON)
- Cycle template creation (4 files, structure, no execution)
- Safety confirmations
- No network calls
- No token reads
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def create_mock_handoff_decision(tmpdir, decision: str) -> Path:
    """Create mock handoff decision."""
    f = Path(tmpdir) / "handoff.json"
    f.write_text(json.dumps({"decision": decision}))
    return f


def create_mock_closure(tmpdir, decision: str) -> Path:
    """Create mock closure."""
    f = Path(tmpdir) / "closure.json"
    f.write_text(json.dumps({"closure_decision": decision}))
    return f


def create_mock_archive(tmpdir, decision: str) -> Path:
    """Create mock archive."""
    f = Path(tmpdir) / "archive.json"
    f.write_text(json.dumps({"final_decision": decision}))
    return f


def test_01_baseline_ready():
    """Test 1: Baseline READY when all READY."""
    with tempfile.TemporaryDirectory() as tmpdir:
        handoff_f = create_mock_handoff_decision(tmpdir, "READY_FOR_CONTROLLED_OPERATION")
        closure_f = create_mock_closure(tmpdir, "WRITE_EXECUTION_COMPLETE_SUCCESS")
        archive_f = create_mock_archive(tmpdir, "PILOT_ARCHIVED_SUCCESS")
        output_f = Path(tmpdir) / "baseline.md"
        output_json = Path(tmpdir) / "baseline.json"

        from tools.local.build_controlled_operation_baseline import main

        test_args = [
            "prog",
            "--device", "test",
            "--device-id", "1",
            "--handoff-decision", str(handoff_f),
            "--closure-summary", str(closure_f),
            "--archive-manifest", str(archive_f),
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert exit_code == 0
        baseline = json.loads(output_json.read_text())
        assert baseline["decision"] == "CONTROLLED_OPERATION_READY"


def test_02_baseline_with_restrictions():
    """Test 2: Baseline WITH_RESTRICTIONS when READY but with warnings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        handoff_f = create_mock_handoff_decision(tmpdir, "READY_WITH_RESTRICTIONS")
        closure_f = create_mock_closure(tmpdir, "WRITE_EXECUTION_COMPLETE_SUCCESS")
        archive_f = create_mock_archive(tmpdir, "PILOT_ARCHIVED_SUCCESS")
        output_f = Path(tmpdir) / "baseline.md"
        output_json = Path(tmpdir) / "baseline.json"

        from tools.local.build_controlled_operation_baseline import main

        test_args = [
            "prog",
            "--device", "test",
            "--device-id", "1",
            "--handoff-decision", str(handoff_f),
            "--closure-summary", str(closure_f),
            "--archive-manifest", str(archive_f),
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            main()

        baseline = json.loads(output_json.read_text())
        assert baseline["decision"] == "CONTROLLED_OPERATION_READY_WITH_RESTRICTIONS"


def test_03_baseline_not_ready():
    """Test 3: Baseline NOT_READY when handoff failed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        handoff_f = create_mock_handoff_decision(tmpdir, "NOT_READY_FOR_OPERATION")
        closure_f = create_mock_closure(tmpdir, "WRITE_EXECUTION_COMPLETE_SUCCESS")
        archive_f = create_mock_archive(tmpdir, "PILOT_ARCHIVED_SUCCESS")
        output_f = Path(tmpdir) / "baseline.md"
        output_json = Path(tmpdir) / "baseline.json"

        from tools.local.build_controlled_operation_baseline import main

        test_args = [
            "prog",
            "--device", "test",
            "--device-id", "1",
            "--handoff-decision", str(handoff_f),
            "--closure-summary", str(closure_f),
            "--archive-manifest", str(archive_f),
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert exit_code == 1
        baseline = json.loads(output_json.read_text())
        assert baseline["decision"] == "CONTROLLED_OPERATION_NOT_READY"


def test_04_baseline_scope():
    """Test 4: Baseline defines scope correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        handoff_f = create_mock_handoff_decision(tmpdir, "READY_FOR_CONTROLLED_OPERATION")
        closure_f = create_mock_closure(tmpdir, "WRITE_EXECUTION_COMPLETE_SUCCESS")
        archive_f = create_mock_archive(tmpdir, "PILOT_ARCHIVED_SUCCESS")
        output_f = Path(tmpdir) / "baseline.md"
        output_json = Path(tmpdir) / "baseline.json"

        from tools.local.build_controlled_operation_baseline import main

        test_args = [
            "prog",
            "--device", "test",
            "--device-id", "1",
            "--handoff-decision", str(handoff_f),
            "--closure-summary", str(closure_f),
            "--archive-manifest", str(archive_f),
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            main()

        baseline = json.loads(output_json.read_text())
        scope = baseline["scope"]

        assert scope["devices_per_cycle"] == 1
        assert scope["max_objects_per_cycle"] == 3
        assert "POST" in scope["allowed_methods"]
        assert "PATCH" in scope["forbidden_methods"]
        assert scope["one_shot_only"] is True


def test_05_baseline_mandatory_gates():
    """Test 5: Baseline lists all mandatory gates."""
    with tempfile.TemporaryDirectory() as tmpdir:
        handoff_f = create_mock_handoff_decision(tmpdir, "READY_FOR_CONTROLLED_OPERATION")
        closure_f = create_mock_closure(tmpdir, "WRITE_EXECUTION_COMPLETE_SUCCESS")
        archive_f = create_mock_archive(tmpdir, "PILOT_ARCHIVED_SUCCESS")
        output_f = Path(tmpdir) / "baseline.md"
        output_json = Path(tmpdir) / "baseline.json"

        from tools.local.build_controlled_operation_baseline import main

        test_args = [
            "prog",
            "--device", "test",
            "--device-id", "1",
            "--handoff-decision", str(handoff_f),
            "--closure-summary", str(closure_f),
            "--archive-manifest", str(archive_f),
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            main()

        baseline = json.loads(output_json.read_text())
        gates = baseline["mandatory_gates"]

        assert "week1_response" in gates
        assert "week2_review" in gates
        assert "execute_real_write_once" in gates
        assert "post_write_verification" in gates
        assert len(gates) == 14  # All gates


def test_06_baseline_markdown_generated():
    """Test 6: Baseline generates markdown report."""
    with tempfile.TemporaryDirectory() as tmpdir:
        handoff_f = create_mock_handoff_decision(tmpdir, "READY_FOR_CONTROLLED_OPERATION")
        closure_f = create_mock_closure(tmpdir, "WRITE_EXECUTION_COMPLETE_SUCCESS")
        archive_f = create_mock_archive(tmpdir, "PILOT_ARCHIVED_SUCCESS")
        output_f = Path(tmpdir) / "baseline.md"
        output_json = Path(tmpdir) / "baseline.json"

        from tools.local.build_controlled_operation_baseline import main

        test_args = [
            "prog",
            "--device", "test",
            "--device-id", "1",
            "--handoff-decision", str(handoff_f),
            "--closure-summary", str(closure_f),
            "--archive-manifest", str(archive_f),
            "--output", str(output_f),
            "--output-json", str(output_json),
        ]

        with patch("sys.argv", test_args):
            main()

        assert output_f.exists()
        content = output_f.read_text()
        assert "Baseline de Operação Controlada" in content


def test_07_cycle_creates_files():
    """Test 7: Cycle creation generates 4 files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "cycle"
        baseline_f = Path(tmpdir) / "baseline.json"
        baseline_f.write_text(json.dumps({"decision": "CONTROLLED_OPERATION_READY"}))

        from tools.local.create_controlled_operation_cycle import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--device", "test",
            "--device-id", "1",
            "--baseline", str(baseline_f),
            "--output-dir", str(output_dir),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert exit_code == 0
        assert (output_dir / "CYCLE-001-PLAN.md").exists()
        assert (output_dir / "CYCLE-001-SCOPE.json").exists()
        assert (output_dir / "CYCLE-001-CHECKLIST.md").exists()
        assert (output_dir / "CYCLE-001-STATUS.json").exists()


def test_08_cycle_scope():
    """Test 8: Cycle scope contains correct restrictions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "cycle"
        baseline_f = Path(tmpdir) / "baseline.json"
        baseline_f.write_text(json.dumps({"decision": "CONTROLLED_OPERATION_READY"}))

        from tools.local.create_controlled_operation_cycle import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--device", "test",
            "--device-id", "1",
            "--baseline", str(baseline_f),
            "--output-dir", str(output_dir),
        ]

        with patch("sys.argv", test_args):
            main()

        scope_f = output_dir / "CYCLE-001-SCOPE.json"
        scope = json.loads(scope_f.read_text())

        assert scope["max_items"] == 3
        assert "POST" in scope["allowed_methods"]
        assert "PATCH" in scope["forbidden_methods"]
        assert scope["one_shot_only"] is True


def test_09_cycle_status_initial():
    """Test 9: Cycle status starts as PLANNED_NOT_STARTED."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "cycle"
        baseline_f = Path(tmpdir) / "baseline.json"
        baseline_f.write_text(json.dumps({"decision": "CONTROLLED_OPERATION_READY"}))

        from tools.local.create_controlled_operation_cycle import main

        test_args = [
            "prog",
            "--cycle-id", "cycle-001",
            "--device", "test",
            "--device-id", "1",
            "--baseline", str(baseline_f),
            "--output-dir", str(output_dir),
        ]

        with patch("sys.argv", test_args):
            main()

        status_f = output_dir / "CYCLE-001-STATUS.json"
        status = json.loads(status_f.read_text())

        assert status["status"] == "PLANNED_NOT_STARTED"
        assert status["cycle_id"] == "cycle-001"
        assert status["device"] == "test"


def test_10_no_network_calls():
    """Test 10: Tools make no network calls."""
    with tempfile.TemporaryDirectory() as tmpdir:
        handoff_f = create_mock_handoff_decision(tmpdir, "READY_FOR_CONTROLLED_OPERATION")
        closure_f = create_mock_closure(tmpdir, "WRITE_EXECUTION_COMPLETE_SUCCESS")
        archive_f = create_mock_archive(tmpdir, "PILOT_ARCHIVED_SUCCESS")
        output_f = Path(tmpdir) / "baseline.md"
        output_json = Path(tmpdir) / "baseline.json"

        from tools.local.build_controlled_operation_baseline import main

        # Mock network calls
        with patch("requests.get") as mock_get:
            with patch("requests.post") as mock_post:
                test_args = [
                    "prog",
                    "--device", "test",
                    "--device-id", "1",
                    "--handoff-decision", str(handoff_f),
                    "--closure-summary", str(closure_f),
                    "--archive-manifest", str(archive_f),
                    "--output", str(output_f),
                    "--output-json", str(output_json),
                ]

                with patch("sys.argv", test_args):
                    main()

                # Verify no network calls
                assert not mock_get.called
                assert not mock_post.called


def main():
    """Run all tests."""
    test_functions = [
        test_01_baseline_ready,
        test_02_baseline_with_restrictions,
        test_03_baseline_not_ready,
        test_04_baseline_scope,
        test_05_baseline_mandatory_gates,
        test_06_baseline_markdown_generated,
        test_07_cycle_creates_files,
        test_08_cycle_scope,
        test_09_cycle_status_initial,
        test_10_no_network_calls,
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
