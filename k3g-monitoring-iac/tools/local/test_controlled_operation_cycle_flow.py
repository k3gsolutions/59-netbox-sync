#!/usr/bin/env python3
"""Test FASES 4.2, 4.3, 4.4: Controlled Operation Cycle Flow.

15 test cases covering:
- Intake validation (max_items, methods, targets)
- Week 1 preparation (structure, status, instructions)
- Metrics collection (cycles, items, guardrails)
- No network calls, no writes, no tokens
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def create_mock_scope(tmpdir, max_items=3, post_only=True) -> Path:
    """Create mock scope JSON."""
    f = Path(tmpdir) / "scope.json"
    scope = {
        "cycle_id": "cycle-001",
        "device": "test",
        "device_id": "1",
        "status": "planned",
        "max_items": max_items,
        "allowed_methods": ["POST"] if post_only else ["POST", "PATCH"],
        "forbidden_methods": ["PATCH", "DELETE"] if post_only else [],
        "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
        "one_shot_only": True,
        "no_automatic_retry": True,
        "no_automatic_rollback": True,
    }
    f.write_text(json.dumps(scope))
    return f


def create_mock_status(tmpdir, status="PLANNED_NOT_STARTED") -> Path:
    """Create mock status JSON."""
    f = Path(tmpdir) / "status.json"
    data = {
        "cycle_id": "cycle-001",
        "device": "test",
        "device_id": "1",
        "status": status,
        "created_at": "2026-04-29T00:00:00+00:00",
    }
    f.write_text(json.dumps(data))
    return f


def test_01_intake_validates_max_items():
    """Test 1: Intake validates max_items <= 3."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        cycle_dir = tmpdir / "cycle"
        cycle_dir.mkdir()
        output_f = cycle_dir / "intake.md"
        output_json = cycle_dir / "intake.json"

        scope = {
            "max_items": 3,
            "allowed_methods": ["POST"],
            "forbidden_methods": ["PATCH", "DELETE"],
            "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
            "one_shot_only": True,
            "no_automatic_retry": True,
            "no_automatic_rollback": True,
        }
        (cycle_dir / "CYCLE-001-SCOPE.json").write_text(json.dumps(scope))
        (cycle_dir / "CYCLE-001-STATUS.json").write_text(json.dumps({"status": "PLANNED_NOT_STARTED"}))

        from tools.local.controlled_cycle_intake import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "test",
            "--device-id",
            "1",
            "--cycle-dir",
            str(cycle_dir),
            "--output",
            str(output_f),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert exit_code == 0
        result = json.loads(output_json.read_text())
        assert result["decision"] == "CYCLE_INTAKE_READY"


def test_02_intake_blocks_excessive_items():
    """Test 2: Intake blocks max_items > 3."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        cycle_dir = tmpdir / "cycle"
        cycle_dir.mkdir()
        scope_f = tmpdir / "scope.json"
        status_f = tmpdir / "status.json"
        output_f = cycle_dir / "intake.md"
        output_json = cycle_dir / "intake.json"

        scope = {
            "max_items": 5,
            "allowed_methods": ["POST"],
            "forbidden_methods": ["PATCH", "DELETE"],
            "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
            "one_shot_only": True,
            "no_automatic_retry": True,
            "no_automatic_rollback": True,
        }
        scope_f.write_text(json.dumps(scope))
        status_f.write_text(json.dumps({"status": "PLANNED_NOT_STARTED"}))

        from tools.local.controlled_cycle_intake import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "test",
            "--device-id",
            "1",
            "--cycle-dir",
            str(cycle_dir),
            "--output",
            str(output_f),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert exit_code == 1
        result = json.loads(output_json.read_text())
        assert "BLOCKED" in result["decision"]


def test_03_intake_requires_post_only():
    """Test 3: Intake requires POST in allowed_methods."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        cycle_dir = tmpdir / "cycle"
        cycle_dir.mkdir()
        scope_f = tmpdir / "scope.json"
        status_f = tmpdir / "status.json"
        output_f = cycle_dir / "intake.md"
        output_json = cycle_dir / "intake.json"

        scope = {
            "max_items": 3,
            "allowed_methods": ["PATCH"],
            "forbidden_methods": ["PATCH", "DELETE"],
            "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
            "one_shot_only": True,
            "no_automatic_retry": True,
            "no_automatic_rollback": True,
        }
        scope_f.write_text(json.dumps(scope))
        status_f.write_text(json.dumps({"status": "PLANNED_NOT_STARTED"}))

        from tools.local.controlled_cycle_intake import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "test",
            "--device-id",
            "1",
            "--cycle-dir",
            str(cycle_dir),
            "--output",
            str(output_f),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert exit_code == 1


def test_04_intake_requires_patch_forbidden():
    """Test 4: Intake requires PATCH in forbidden_methods."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        cycle_dir = tmpdir / "cycle"
        cycle_dir.mkdir()
        scope_f = tmpdir / "scope.json"
        status_f = tmpdir / "status.json"
        output_f = cycle_dir / "intake.md"
        output_json = cycle_dir / "intake.json"

        scope = {
            "max_items": 3,
            "allowed_methods": ["POST"],
            "forbidden_methods": ["DELETE"],
            "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
            "one_shot_only": True,
            "no_automatic_retry": True,
            "no_automatic_rollback": True,
        }
        scope_f.write_text(json.dumps(scope))
        status_f.write_text(json.dumps({"status": "PLANNED_NOT_STARTED"}))

        from tools.local.controlled_cycle_intake import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "test",
            "--device-id",
            "1",
            "--cycle-dir",
            str(cycle_dir),
            "--output",
            str(output_f),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert exit_code == 1


def test_05_intake_requires_sync_forbidden():
    """Test 5: Intake requires /sync in forbidden_targets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        cycle_dir = tmpdir / "cycle"
        cycle_dir.mkdir()
        scope_f = tmpdir / "scope.json"
        status_f = tmpdir / "status.json"
        output_f = cycle_dir / "intake.md"
        output_json = cycle_dir / "intake.json"

        scope = {
            "max_items": 3,
            "allowed_methods": ["POST"],
            "forbidden_methods": ["PATCH", "DELETE"],
            "forbidden_targets": ["equipment", "ssh", "netconf"],
            "one_shot_only": True,
            "no_automatic_retry": True,
            "no_automatic_rollback": True,
        }
        scope_f.write_text(json.dumps(scope))
        status_f.write_text(json.dumps({"status": "PLANNED_NOT_STARTED"}))

        from tools.local.controlled_cycle_intake import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "test",
            "--device-id",
            "1",
            "--cycle-dir",
            str(cycle_dir),
            "--output",
            str(output_f),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert exit_code == 1


def test_06_intake_generates_markdown():
    """Test 6: Intake generates markdown report."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        cycle_dir = tmpdir / "cycle"
        cycle_dir.mkdir()
        output_f = cycle_dir / "intake.md"
        output_json = cycle_dir / "intake.json"

        scope = {
            "max_items": 3,
            "allowed_methods": ["POST"],
            "forbidden_methods": ["PATCH", "DELETE"],
            "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
            "one_shot_only": True,
            "no_automatic_retry": True,
            "no_automatic_rollback": True,
        }
        (cycle_dir / "CYCLE-001-SCOPE.json").write_text(json.dumps(scope))
        (cycle_dir / "CYCLE-001-STATUS.json").write_text(json.dumps({"status": "PLANNED_NOT_STARTED"}))

        from tools.local.controlled_cycle_intake import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "test",
            "--device-id",
            "1",
            "--cycle-dir",
            str(cycle_dir),
            "--output",
            str(output_f),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            main()

        assert output_f.exists()
        content = output_f.read_text()
        assert "CYCLE_INTAKE" in content


def test_07_week1_creates_structure():
    """Test 7: Week 1 prepare creates directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        output_dir = tmpdir / "week1"

        from tools.local.controlled_cycle_week1_prepare import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "test",
            "--device-id",
            "1",
            "--cycle-dir",
            str(tmpdir),
            "--output-dir",
            str(output_dir),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert exit_code == 0
        assert (output_dir / "responses").exists()
        assert (output_dir / "CYCLE-001-WEEK1-PLAN.md").exists()
        assert (output_dir / "CYCLE-001-WEEK1-CHECKLIST.md").exists()
        assert (output_dir / "CYCLE-001-WEEK1-STATUS.json").exists()


def test_08_week1_status_ready():
    """Test 8: Week 1 status is WEEK1_READY_FOR_RESPONSES."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        output_dir = tmpdir / "week1"

        from tools.local.controlled_cycle_week1_prepare import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "test",
            "--device-id",
            "1",
            "--cycle-dir",
            str(tmpdir),
            "--output-dir",
            str(output_dir),
        ]

        with patch("sys.argv", test_args):
            main()

        status_file = output_dir / "CYCLE-001-WEEK1-STATUS.json"
        status = json.loads(status_file.read_text())
        assert status["status"] == "WEEK1_READY_FOR_RESPONSES"


def test_09_week1_no_writes():
    """Test 9: Week 1 prepare makes no NetBox writes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        output_dir = tmpdir / "week1"

        from tools.local.controlled_cycle_week1_prepare import main

        with patch("requests.post") as mock_post:
            with patch("requests.patch") as mock_patch:
                test_args = [
                    "prog",
                    "--cycle-id",
                    "cycle-001",
                    "--device",
                    "test",
                    "--device-id",
                    "1",
                    "--cycle-dir",
                    str(tmpdir),
                    "--output-dir",
                    str(output_dir),
                ]

                with patch("sys.argv", test_args):
                    main()

                assert not mock_post.called
                assert not mock_patch.called


def test_10_metrics_collects_cycles():
    """Test 10: Metrics collects cycle data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        cycle_dir = tmpdir / "cycle-001"
        cycle_dir.mkdir()
        output_f = tmpdir / "metrics.md"
        output_json = tmpdir / "metrics.json"

        # Create minimal cycle structure
        status = {"status": "PLANNED_NOT_STARTED", "cycle_id": "cycle-001"}
        (cycle_dir / "CYCLE-001-STATUS.json").write_text(json.dumps(status))

        from tools.local.controlled_operation_metrics import main

        test_args = [
            "prog",
            "--root",
            str(tmpdir),
            "--output",
            str(output_f),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert exit_code == 0
        result = json.loads(output_json.read_text())
        assert result["total_cycles"] == 1


def test_11_metrics_no_token_read():
    """Test 11: Metrics doesn't read tokens."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        output_f = tmpdir / "metrics.md"
        output_json = tmpdir / "metrics.json"

        from tools.local.controlled_operation_metrics import main

        with patch("os.environ.get") as mock_env:
            test_args = [
                "prog",
                "--root",
                str(tmpdir),
                "--output",
                str(output_f),
                "--output-json",
                str(output_json),
            ]

            with patch("sys.argv", test_args):
                main()

            # Verify no calls to os.environ for NETBOX_WRITE_TOKEN
            calls = [call for call in mock_env.call_args_list if "TOKEN" in str(call)]
            assert len(calls) == 0


def test_12_metrics_generates_json():
    """Test 12: Metrics generates JSON output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        output_f = tmpdir / "metrics.md"
        output_json = tmpdir / "metrics.json"

        from tools.local.controlled_operation_metrics import main

        test_args = [
            "prog",
            "--root",
            str(tmpdir),
            "--output",
            str(output_f),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            main()

        assert output_json.exists()
        result = json.loads(output_json.read_text())
        assert "generated_at" in result
        assert "total_cycles" in result


def test_13_intake_no_approvalrecord_created():
    """Test 13: Intake doesn't create ApprovalRecord."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        cycle_dir = tmpdir / "cycle"
        cycle_dir.mkdir()
        output_f = cycle_dir / "intake.md"
        output_json = cycle_dir / "intake.json"

        scope = {
            "max_items": 3,
            "allowed_methods": ["POST"],
            "forbidden_methods": ["PATCH", "DELETE"],
            "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
            "one_shot_only": True,
            "no_automatic_retry": True,
            "no_automatic_rollback": True,
        }
        (cycle_dir / "CYCLE-001-SCOPE.json").write_text(json.dumps(scope))
        (cycle_dir / "CYCLE-001-STATUS.json").write_text(json.dumps({"status": "PLANNED_NOT_STARTED"}))

        from tools.local.controlled_cycle_intake import main

        with patch("requests.post") as mock_post:
            test_args = [
                "prog",
                "--cycle-id",
                "cycle-001",
                "--device",
                "test",
                "--device-id",
                "1",
                "--cycle-dir",
                str(cycle_dir),
                "--output",
                str(output_f),
                "--output-json",
                str(output_json),
            ]

            with patch("sys.argv", test_args):
                main()

            assert not mock_post.called


def test_14_week1_no_applyplan_created():
    """Test 14: Week 1 prepare doesn't create ApplyPlan."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        output_dir = tmpdir / "week1"

        from tools.local.controlled_cycle_week1_prepare import main

        with patch("requests.post") as mock_post:
            test_args = [
                "prog",
                "--cycle-id",
                "cycle-001",
                "--device",
                "test",
                "--device-id",
                "1",
                "--cycle-dir",
                str(tmpdir),
                "--output-dir",
                str(output_dir),
            ]

            with patch("sys.argv", test_args):
                main()

            assert not mock_post.called


def test_15_full_cycle_flow_no_netbox_writes():
    """Test 15: Full cycle flow (intake + week1 + metrics) makes no writes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        cycle_dir = tmpdir / "cycle"
        cycle_dir.mkdir()

        scope = {
            "max_items": 3,
            "allowed_methods": ["POST"],
            "forbidden_methods": ["PATCH", "DELETE"],
            "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
            "one_shot_only": True,
            "no_automatic_retry": True,
            "no_automatic_rollback": True,
        }
        (cycle_dir / "CYCLE-001-SCOPE.json").write_text(json.dumps(scope))
        (cycle_dir / "CYCLE-001-STATUS.json").write_text(json.dumps({"status": "PLANNED_NOT_STARTED"}))

        from tools.local.controlled_cycle_intake import main as intake_main
        from tools.local.controlled_cycle_week1_prepare import main as week1_main
        from tools.local.controlled_operation_metrics import main as metrics_main

        # Run all three
        with patch("requests.post") as mock_post:
            with patch("requests.patch") as mock_patch:
                with patch("requests.delete") as mock_delete:
                    # Intake
                    test_args = [
                        "prog",
                        "--cycle-id",
                        "cycle-001",
                        "--device",
                        "test",
                        "--device-id",
                        "1",
                        "--cycle-dir",
                        str(cycle_dir),
                        "--output",
                        str(cycle_dir / "intake.md"),
                        "--output-json",
                        str(cycle_dir / "intake.json"),
                    ]
                    with patch("sys.argv", test_args):
                        intake_main()

                    # Week 1
                    test_args = [
                        "prog",
                        "--cycle-id",
                        "cycle-001",
                        "--device",
                        "test",
                        "--device-id",
                        "1",
                        "--cycle-dir",
                        str(cycle_dir),
                        "--output-dir",
                        str(cycle_dir / "week1"),
                    ]
                    with patch("sys.argv", test_args):
                        week1_main()

                    # Metrics
                    test_args = [
                        "prog",
                        "--root",
                        str(tmpdir),
                        "--output",
                        str(tmpdir / "metrics.md"),
                        "--output-json",
                        str(tmpdir / "metrics.json"),
                    ]
                    with patch("sys.argv", test_args):
                        metrics_main()

                    assert not mock_post.called
                    assert not mock_patch.called
                    assert not mock_delete.called


def main():
    """Run all tests."""
    test_functions = [
        test_01_intake_validates_max_items,
        test_02_intake_blocks_excessive_items,
        test_03_intake_requires_post_only,
        test_04_intake_requires_patch_forbidden,
        test_05_intake_requires_sync_forbidden,
        test_06_intake_generates_markdown,
        test_07_week1_creates_structure,
        test_08_week1_status_ready,
        test_09_week1_no_writes,
        test_10_metrics_collects_cycles,
        test_11_metrics_no_token_read,
        test_12_metrics_generates_json,
        test_13_intake_no_approvalrecord_created,
        test_14_week1_no_applyplan_created,
        test_15_full_cycle_flow_no_netbox_writes,
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
