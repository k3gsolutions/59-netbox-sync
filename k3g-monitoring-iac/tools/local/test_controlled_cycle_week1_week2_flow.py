#!/usr/bin/env python3
"""Test FASES 4.5, 4.6, 4.7: Week 1-2 Response & Review Flow.

16 test cases covering:
- Week 1 intake (response counting, classification)
- Week 1 validation (compliance checks, secret blocking)
- Week 2 preparation (review board, decisions CSV)
- No writes, no tokens, no ApprovalRecord/ApplyPlan creation
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def create_mock_response(tmpdir, team="service", status="submitted") -> Path:
    """Create mock response JSON."""
    f = Path(tmpdir) / f"response-{team}-001.json"
    response = {
        "cycle_id": "cycle-001",
        "device": "4WNET-MNS-KTG-RX",
        "device_id": "1890",
        "team": team,
        "object_type": "interface",
        "object_id": "Eth-Trunk0",
        "item_id": "Eth-Trunk0",
        "owner": "operator@example.com",
        "status": status,
        "response": {"description": "Test interface"},
        "notes": "Valid response",
    }
    f.write_text(json.dumps(response))
    return f


def test_01_intake_counts_responses():
    """Test 1: Intake counts responses correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        responses_dir = tmpdir / "responses"
        responses_dir.mkdir()
        output_f = tmpdir / "intake.md"
        output_json = tmpdir / "intake.json"

        # Create mock responses
        create_mock_response(responses_dir, "service")
        create_mock_response(responses_dir, "network_ops")

        # Create scope
        scope = {"max_items": 3}
        (tmpdir / "CYCLE-001-SCOPE.json").write_text(json.dumps(scope))

        from tools.local.controlled_cycle_week1_response_intake import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--cycle-dir",
            str(tmpdir),
            "--responses-dir",
            str(responses_dir),
            "--output",
            str(output_f),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            main()

        result = json.loads(output_json.read_text())
        assert result["response_counts"]["total_items"] == 2


def test_02_intake_classifies_by_team():
    """Test 2: Intake classifies responses by team."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        responses_dir = tmpdir / "responses"
        responses_dir.mkdir()
        output_f = tmpdir / "intake.md"
        output_json = tmpdir / "intake.json"

        create_mock_response(responses_dir, "service")
        create_mock_response(responses_dir, "bgp")

        scope = {"max_items": 3}
        (tmpdir / "CYCLE-001-SCOPE.json").write_text(json.dumps(scope))

        from tools.local.controlled_cycle_week1_response_intake import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--cycle-dir",
            str(tmpdir),
            "--responses-dir",
            str(responses_dir),
            "--output",
            str(output_f),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            main()

        result = json.loads(output_json.read_text())
        assert result["response_counts"]["by_team"]["service"]["count"] == 1
        assert result["response_counts"]["by_team"]["bgp"]["count"] == 1


def test_03_intake_decision_ready_when_max_items():
    """Test 3: Intake ready when responses >= max_items."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        responses_dir = tmpdir / "responses"
        responses_dir.mkdir()
        output_f = tmpdir / "intake.md"
        output_json = tmpdir / "intake.json"

        create_mock_response(responses_dir, "service")
        create_mock_response(responses_dir, "network_ops")
        create_mock_response(responses_dir, "bgp")

        scope = {"max_items": 3}
        (tmpdir / "CYCLE-001-SCOPE.json").write_text(json.dumps(scope))

        from tools.local.controlled_cycle_week1_response_intake import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--cycle-dir",
            str(tmpdir),
            "--responses-dir",
            str(responses_dir),
            "--output",
            str(output_f),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert result["decision"] == "WEEK1_INTAKE_READY"
        assert exit_code == 0


def test_04_intake_decision_partial_when_some():
    """Test 4: Intake partial when some responses < max_items."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        responses_dir = tmpdir / "responses"
        responses_dir.mkdir()
        output_f = tmpdir / "intake.md"
        output_json = tmpdir / "intake.json"

        create_mock_response(responses_dir, "service")

        scope = {"max_items": 3}
        (tmpdir / "CYCLE-001-SCOPE.json").write_text(json.dumps(scope))

        from tools.local.controlled_cycle_week1_response_intake import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--cycle-dir",
            str(tmpdir),
            "--responses-dir",
            str(responses_dir),
            "--output",
            str(output_f),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            main()

        result = json.loads(output_json.read_text())
        assert result["decision"] == "WEEK1_INTAKE_PARTIAL"


def test_05_validation_blocks_secret():
    """Test 5: Validation blocks response with secret."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        responses_dir = tmpdir / "responses"
        responses_dir.mkdir()
        output_f = tmpdir / "validation.md"
        output_json = tmpdir / "validation.json"

        # Create response with secret word
        f = responses_dir / "response-001.json"
        response = {
            "device": "4WNET-MNS-KTG-RX",
            "object_type": "interface",
            "owner": "user@example.com",
            "notes": "token: secret123",
            "status": "submitted",
        }
        f.write_text(json.dumps(response))

        from tools.local.controlled_cycle_week1_validate import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--cycle-dir",
            str(tmpdir),
            "--responses-dir",
            str(responses_dir),
            "--output",
            str(output_f),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            main()

        result = json.loads(output_json.read_text())
        assert result["summary"]["blocked"] > 0


def test_06_validation_accepts_valid():
    """Test 6: Validation accepts valid response."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        responses_dir = tmpdir / "responses"
        responses_dir.mkdir()
        output_f = tmpdir / "validation.md"
        output_json = tmpdir / "validation.json"

        create_mock_response(responses_dir, "service")

        from tools.local.controlled_cycle_week1_validate import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--cycle-dir",
            str(tmpdir),
            "--responses-dir",
            str(responses_dir),
            "--output",
            str(output_f),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            main()

        result = json.loads(output_json.read_text())
        assert result["summary"]["valid"] > 0


def test_07_validation_decision_passed():
    """Test 7: Validation passed when all valid."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        responses_dir = tmpdir / "responses"
        responses_dir.mkdir()
        output_f = tmpdir / "validation.md"
        output_json = tmpdir / "validation.json"

        create_mock_response(responses_dir, "service")

        from tools.local.controlled_cycle_week1_validate import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--cycle-dir",
            str(tmpdir),
            "--responses-dir",
            str(responses_dir),
            "--output",
            str(output_f),
            "--output-json",
            str(output_json),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        result = json.loads(output_json.read_text())
        assert "PASSED" in result["decision"]
        assert exit_code == 0


def test_08_week2_prepare_creates_structure():
    """Test 8: Week 2 prepare creates directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        week2_dir = tmpdir / "week2"
        week2_validation = tmpdir / "validation.json"

        validation = {"summary": {"valid": 2, "blocked": 0, "total_responses": 2}}
        week2_validation.write_text(json.dumps(validation))

        from tools.local.controlled_cycle_week2_prepare import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--cycle-dir",
            str(tmpdir),
            "--week1-validation",
            str(week2_validation),
            "--output-dir",
            str(week2_dir),
        ]

        with patch("sys.argv", test_args):
            exit_code = main()

        assert exit_code == 0
        assert (week2_dir / "CYCLE-001-WEEK2-PLAN.md").exists()
        assert (week2_dir / "CYCLE-001-WEEK2-REVIEW-BOARD.md").exists()
        assert (week2_dir / "CYCLE-001-WEEK2-DECISIONS.csv").exists()
        assert (week2_dir / "CYCLE-001-WEEK2-STATUS.json").exists()
        assert (week2_dir / "approval-drafts").exists()


def test_09_week2_generates_decisions_csv():
    """Test 9: Week 2 generates decisions CSV."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        week2_dir = tmpdir / "week2"
        week2_validation = tmpdir / "validation.json"

        validation = {"summary": {"valid": 2, "blocked": 0, "total_responses": 2}}
        week2_validation.write_text(json.dumps(validation))

        from tools.local.controlled_cycle_week2_prepare import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--cycle-dir",
            str(tmpdir),
            "--week1-validation",
            str(week2_validation),
            "--output-dir",
            str(week2_dir),
        ]

        with patch("sys.argv", test_args):
            main()

        decisions_file = week2_dir / "CYCLE-001-WEEK2-DECISIONS.csv"
        assert decisions_file.exists()
        content = decisions_file.read_text()
        assert "item_id" in content
        assert "decision" in content
        assert "reviewed_by" in content


def test_10_week2_generates_approval_drafts():
    """Test 10: Week 2 generates approval drafts (local only)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        week2_dir = tmpdir / "week2"
        week2_validation = tmpdir / "validation.json"

        validation = {"summary": {"valid": 2, "blocked": 0, "total_responses": 2}}
        week2_validation.write_text(json.dumps(validation))

        from tools.local.controlled_cycle_week2_prepare import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--cycle-dir",
            str(tmpdir),
            "--week1-validation",
            str(week2_validation),
            "--output-dir",
            str(week2_dir),
        ]

        with patch("sys.argv", test_args):
            main()

        draft_dir = week2_dir / "approval-drafts"
        drafts = list(draft_dir.glob("*.json"))
        assert len(drafts) == 2

        draft = json.loads(drafts[0].read_text())
        assert draft["status"] == "draft"
        assert "draft-cycle-001" in draft["approval_id"]


def test_11_week2_decision_ready_when_valid():
    """Test 11: Week 2 decision ready when valid responses."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        week2_dir = tmpdir / "week2"
        week2_validation = tmpdir / "validation.json"

        validation = {"summary": {"valid": 2, "blocked": 0, "total_responses": 2}}
        week2_validation.write_text(json.dumps(validation))

        from tools.local.controlled_cycle_week2_prepare import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--cycle-dir",
            str(tmpdir),
            "--week1-validation",
            str(week2_validation),
            "--output-dir",
            str(week2_dir),
        ]

        with patch("sys.argv", test_args):
            main()

        status_file = week2_dir / "CYCLE-001-WEEK2-STATUS.json"
        status = json.loads(status_file.read_text())
        assert status["status"] == "WEEK2_PREPARATION_READY"


def test_12_week2_decision_blocked_when_no_valid():
    """Test 12: Week 2 decision blocked when no valid responses."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        week2_dir = tmpdir / "week2"
        week2_validation = tmpdir / "validation.json"

        validation = {"summary": {"valid": 0, "blocked": 1, "total_responses": 1}}
        week2_validation.write_text(json.dumps(validation))

        from tools.local.controlled_cycle_week2_prepare import main

        test_args = [
            "prog",
            "--cycle-id",
            "cycle-001",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--cycle-dir",
            str(tmpdir),
            "--week1-validation",
            str(week2_validation),
            "--output-dir",
            str(week2_dir),
        ]

        with patch("sys.argv", test_args):
            main()

        status_file = week2_dir / "CYCLE-001-WEEK2-STATUS.json"
        status = json.loads(status_file.read_text())
        assert status["status"] == "WEEK2_PREPARATION_BLOCKED"


def test_13_intake_no_netbox_writes():
    """Test 13: Intake makes no NetBox writes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        responses_dir = tmpdir / "responses"
        responses_dir.mkdir()
        output_f = tmpdir / "intake.md"
        output_json = tmpdir / "intake.json"

        scope = {"max_items": 3}
        (tmpdir / "CYCLE-001-SCOPE.json").write_text(json.dumps(scope))

        from tools.local.controlled_cycle_week1_response_intake import main

        with patch("requests.post") as mock_post:
            with patch("requests.patch") as mock_patch:
                test_args = [
                    "prog",
                    "--cycle-id",
                    "cycle-001",
                    "--device",
                    "4WNET-MNS-KTG-RX",
                    "--device-id",
                    "1890",
                    "--cycle-dir",
                    str(tmpdir),
                    "--responses-dir",
                    str(responses_dir),
                    "--output",
                    str(output_f),
                    "--output-json",
                    str(output_json),
                ]

                with patch("sys.argv", test_args):
                    main()

                assert not mock_post.called
                assert not mock_patch.called


def test_14_validation_no_approval_creation():
    """Test 14: Validation doesn't create ApprovalRecord."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        responses_dir = tmpdir / "responses"
        responses_dir.mkdir()
        output_f = tmpdir / "validation.md"
        output_json = tmpdir / "validation.json"

        create_mock_response(responses_dir, "service")

        from tools.local.controlled_cycle_week1_validate import main

        with patch("requests.post") as mock_post:
            test_args = [
                "prog",
                "--cycle-id",
                "cycle-001",
                "--device",
                "4WNET-MNS-KTG-RX",
                "--device-id",
                "1890",
                "--cycle-dir",
                str(tmpdir),
                "--responses-dir",
                str(responses_dir),
                "--output",
                str(output_f),
                "--output-json",
                str(output_json),
            ]

            with patch("sys.argv", test_args):
                main()

            assert not mock_post.called


def test_15_week2_no_applyplan_creation():
    """Test 15: Week 2 doesn't create ApplyPlan."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        week2_dir = tmpdir / "week2"
        week2_validation = tmpdir / "validation.json"

        validation = {"summary": {"valid": 2, "blocked": 0, "total_responses": 2}}
        week2_validation.write_text(json.dumps(validation))

        from tools.local.controlled_cycle_week2_prepare import main

        with patch("requests.post") as mock_post:
            test_args = [
                "prog",
                "--cycle-id",
                "cycle-001",
                "--device",
                "4WNET-MNS-KTG-RX",
                "--device-id",
                "1890",
                "--cycle-dir",
                str(tmpdir),
                "--week1-validation",
                str(week2_validation),
                "--output-dir",
                str(week2_dir),
            ]

            with patch("sys.argv", test_args):
                main()

            assert not mock_post.called


def test_16_full_week1_week2_no_writes():
    """Test 16: Full week 1-2 flow makes no writes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        responses_dir = tmpdir / "responses"
        responses_dir.mkdir()
        week2_dir = tmpdir / "week2"

        create_mock_response(responses_dir, "service")

        scope = {"max_items": 3}
        (tmpdir / "CYCLE-001-SCOPE.json").write_text(json.dumps(scope))

        from tools.local.controlled_cycle_week1_response_intake import main as intake_main
        from tools.local.controlled_cycle_week1_validate import main as validate_main
        from tools.local.controlled_cycle_week2_prepare import main as week2_main

        with patch("requests.post") as mock_post:
            with patch("requests.patch") as mock_patch:
                with patch("requests.delete") as mock_delete:
                    # Intake
                    test_args = [
                        "prog",
                        "--cycle-id",
                        "cycle-001",
                        "--device",
                        "4WNET-MNS-KTG-RX",
                        "--device-id",
                        "1890",
                        "--cycle-dir",
                        str(tmpdir),
                        "--responses-dir",
                        str(responses_dir),
                        "--output",
                        str(tmpdir / "intake.md"),
                        "--output-json",
                        str(tmpdir / "intake.json"),
                    ]
                    with patch("sys.argv", test_args):
                        intake_main()

                    # Validation
                    test_args = [
                        "prog",
                        "--cycle-id",
                        "cycle-001",
                        "--device",
                        "4WNET-MNS-KTG-RX",
                        "--device-id",
                        "1890",
                        "--cycle-dir",
                        str(tmpdir),
                        "--responses-dir",
                        str(responses_dir),
                        "--output",
                        str(tmpdir / "validation.md"),
                        "--output-json",
                        str(tmpdir / "validation.json"),
                    ]
                    with patch("sys.argv", test_args):
                        validate_main()

                    # Week 2
                    test_args = [
                        "prog",
                        "--cycle-id",
                        "cycle-001",
                        "--device",
                        "4WNET-MNS-KTG-RX",
                        "--device-id",
                        "1890",
                        "--cycle-dir",
                        str(tmpdir),
                        "--week1-validation",
                        str(tmpdir / "validation.json"),
                        "--output-dir",
                        str(week2_dir),
                    ]
                    with patch("sys.argv", test_args):
                        week2_main()

                    assert not mock_post.called
                    assert not mock_patch.called
                    assert not mock_delete.called


def main():
    """Run all tests."""
    test_functions = [
        test_01_intake_counts_responses,
        test_02_intake_classifies_by_team,
        test_03_intake_decision_ready_when_max_items,
        test_04_intake_decision_partial_when_some,
        test_05_validation_blocks_secret,
        test_06_validation_accepts_valid,
        test_07_validation_decision_passed,
        test_08_week2_prepare_creates_structure,
        test_09_week2_generates_decisions_csv,
        test_10_week2_generates_approval_drafts,
        test_11_week2_decision_ready_when_valid,
        test_12_week2_decision_blocked_when_no_valid,
        test_13_intake_no_netbox_writes,
        test_14_validation_no_approval_creation,
        test_15_week2_no_applyplan_creation,
        test_16_full_week1_week2_no_writes,
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
