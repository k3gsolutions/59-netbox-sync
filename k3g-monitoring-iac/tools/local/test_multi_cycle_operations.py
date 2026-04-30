#!/usr/bin/env python3
"""Test suite for multi-cycle operations (FASES 4.30-4.33)."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def create_test_cycle_dir(root: Path, cycle_id: str) -> Path:
    """Create minimal cycle directory."""
    cycle_dir = root / cycle_id
    cycle_dir.mkdir(parents=True, exist_ok=True)

    scope = {
        "cycle_id": cycle_id,
        "device": "test-device",
        "device_id": "1234",
        "status": "PLANNED_NOT_STARTED",
        "max_items": 3,
        "allowed_methods": ["POST"],
        "forbidden_methods": ["PATCH", "DELETE"],
        "forbidden_targets": ["/sync", "equipment", "ssh", "netconf"],
        "requires_week1": True,
        "requires_week2": True,
        "requires_approval_records": True,
        "requires_applyplan_dryrun": True,
        "requires_real_write_authorization": True,
        "requires_post_write_verification": True,
    }
    (cycle_dir / f"{cycle_id.upper()}-SCOPE.json").write_text(json.dumps(scope, indent=2))
    (cycle_dir / f"{cycle_id.upper()}-STATUS.md").write_text("# Status")
    return cycle_dir


def test_01():
    """Test operation index."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        root = tmpdir / "controlled-operation"
        root.mkdir()
        create_test_cycle_dir(root, "cycle-001")

        from tools.local.build_controlled_operation_index import main
        with patch("sys.argv", ["prog", "--root", str(root), "--output", str(tmpdir / "index.md"), "--output-json", str(tmpdir / "index.json")]):
            assert main() == 0

        index = json.loads((tmpdir / "index.json").read_text())
        assert len(index["cycles"]) >= 1
        print("✓ test_01_operation_index")


def test_02():
    """Test start gate."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        root = tmpdir / "controlled-operation"
        root.mkdir()
        c1 = create_test_cycle_dir(root, "cycle-001")
        c2 = create_test_cycle_dir(root, "cycle-002")

        (c1 / "cycle-001-handoff-decision.json").write_text(json.dumps({"decision": "CYCLE_CLOSED_READY_FOR_NEXT_OPERATION"}))

        from tools.local.controlled_cycle_start_gate import main
        (root / "index.json").write_text(json.dumps({"cycles": []}))
        with patch("sys.argv", ["prog", "--cycle-id", "cycle-002", "--previous-cycle", "cycle-001", "--cycle-dir", str(c2),
                                 "--previous-handoff", str(c1 / "cycle-001-handoff-decision.json"), "--operation-index", str(root / "index.json"),
                                 "--output", str(tmpdir / "gate.md"), "--output-json", str(tmpdir / "gate.json")]):
            main()

        result = json.loads((tmpdir / "gate.json").read_text())
        assert result["decision"] in ["CYCLE_START_READY", "CYCLE_START_READY_WITH_RESTRICTIONS"]
        print("✓ test_02_start_gate_ready")


def test_03():
    """Test start gate blocked."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        root = tmpdir / "controlled-operation"
        root.mkdir()
        c1 = create_test_cycle_dir(root, "cycle-001")
        c2 = create_test_cycle_dir(root, "cycle-002")

        (c1 / "cycle-001-handoff-decision.json").write_text(json.dumps({"decision": "CYCLE_ACTION_REQUIRED"}))

        from tools.local.controlled_cycle_start_gate import main
        (root / "index.json").write_text(json.dumps({"cycles": []}))
        with patch("sys.argv", ["prog", "--cycle-id", "cycle-002", "--previous-cycle", "cycle-001", "--cycle-dir", str(c2),
                                 "--previous-handoff", str(c1 / "cycle-001-handoff-decision.json"), "--operation-index", str(root / "index.json"),
                                 "--output", str(tmpdir / "gate.md"), "--output-json", str(tmpdir / "gate.json")]):
            main()

        result = json.loads((tmpdir / "gate.json").read_text())
        assert result["decision"] == "CYCLE_START_BLOCKED"
        print("✓ test_03_start_gate_blocked")


def test_04():
    """Test expansion policy."""
    from tools.local.evaluate_controlled_expansion import load_policy
    with tempfile.TemporaryDirectory() as tmpdir:
        pf = Path(tmpdir) / "policy.yaml"
        pf.write_text("version: '1.0'\ncurrent_limits:\n  max_items_per_cycle: 3\n")
        policy = load_policy(pf)
        assert policy.get("version") == "1.0"
        print("✓ test_04_expansion_policy")


def test_05():
    """Test expansion evaluation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        idx = {"cycles": [{"cycle_id": "c1", "current_status": "closed_success"}, {"cycle_id": "c2", "current_status": "action_required"}]}
        (tmpdir / "index.json").write_text(json.dumps(idx))
        (tmpdir / "policy.yaml").write_text("version: '1.0'\n")

        from tools.local.evaluate_controlled_expansion import main
        (tmpdir / "metrics.json").write_text(json.dumps({}))
        with patch("sys.argv", ["prog", "--metrics", str(tmpdir / "metrics.json"), "--index", str(tmpdir / "index.json"),
                                 "--policy", str(tmpdir / "policy.yaml"), "--output", str(tmpdir / "eval.md"), "--output-json", str(tmpdir / "eval.json")]):
            main()

        result = json.loads((tmpdir / "eval.json").read_text())
        assert result["recommendation"] == "EXPANSION_BLOCKED"
        print("✓ test_05_expansion_evaluation")


def test_06():
    """Test no token access."""
    import inspect
    from tools.local import build_controlled_operation_index
    source = inspect.getsource(build_controlled_operation_index)
    assert "import requests" not in source
    assert "import socket" not in source
    print("✓ test_06_no_token")


def test_07():
    """Test no NetBox writes."""
    import inspect
    from tools.local import build_controlled_operation_index
    source = inspect.getsource(build_controlled_operation_index)
    assert ".post(" not in source
    assert ".patch(" not in source
    assert ".delete(" not in source
    print("✓ test_07_no_netbox_writes")


def test_08():
    """Test json valid."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        root = tmpdir / "controlled-operation"
        root.mkdir()
        create_test_cycle_dir(root, "cycle-001")

        from tools.local.build_controlled_operation_index import main
        with patch("sys.argv", ["prog", "--root", str(root), "--output", str(tmpdir / "index.md"), "--output-json", str(tmpdir / "index.json")]):
            main()

        index = json.loads((tmpdir / "index.json").read_text())
        assert "measured_at" in index
        assert "cycles" in index
        print("✓ test_08_json_valid")


def test_09():
    """Test limits not auto-changed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        idx = {"cycles": [{"cycle_id": f"c{i}", "current_status": "closed_success"} for i in range(1, 6)]}
        (tmpdir / "index.json").write_text(json.dumps(idx))
        (tmpdir / "policy.yaml").write_text("version: '1.0'\ncurrent_limits:\n  max_items_per_cycle: 3\n")

        from tools.local.evaluate_controlled_expansion import main
        (tmpdir / "metrics.json").write_text(json.dumps({}))
        with patch("sys.argv", ["prog", "--metrics", str(tmpdir / "metrics.json"), "--index", str(tmpdir / "index.json"),
                                 "--policy", str(tmpdir / "policy.yaml"), "--output", str(tmpdir / "eval.md"), "--output-json", str(tmpdir / "eval.json")]):
            main()

        result = json.loads((tmpdir / "eval.json").read_text())
        assert result["limits_changed"] is False
        assert result["current_limits"]["max_items_per_cycle"] == 3
        print("✓ test_09_limits_not_auto_changed")


def test_10():
    """Test markdown generated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        root = tmpdir / "controlled-operation"
        root.mkdir()
        create_test_cycle_dir(root, "cycle-001")

        from tools.local.build_controlled_operation_index import main
        with patch("sys.argv", ["prog", "--root", str(root), "--output", str(tmpdir / "index.md"), "--output-json", str(tmpdir / "index.json")]):
            main()

        md = (tmpdir / "index.md").read_text()
        assert "Controlled Operation" in md or "cycle" in md.lower()
        print("✓ test_10_markdown_generated")


if __name__ == "__main__":
    test_01()
    test_02()
    test_03()
    test_04()
    test_05()
    test_06()
    test_07()
    test_08()
    test_09()
    test_10()

    print("\n" + "=" * 60)
    print("Results: 10/10 tests passed")
    print("=" * 60)
