#!/usr/bin/env python3
"""Tests for Cycle-002 Week 1 response seed and Week 2 preparation."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.local.test_cycle002_week1_flow import ASGIClient, make_cycle, run_main

from webui.app import app
from tools.local.controlled_cycle_week1_seed_response import main as seed_main
from tools.local.controlled_cycle_week1_response_intake_v2 import main as intake_main
from tools.local.controlled_cycle_week1_validate_v2 import main as validate_main
from tools.local.controlled_cycle_week2_prepare_v2 import main as week2_prepare_main


ROOT = Path(__file__).parent.parent.parent
TEMPLATE = ROOT / "reports" / "pilot-device-compliance" / "week1-metadata-collection-template.csv"


def _copy_template(tmpdir: Path) -> None:
    dest = tmpdir / "reports" / "pilot-device-compliance"
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TEMPLATE, dest / TEMPLATE.name)


def _seed_common_args(cycle_dir: Path, team: str, object_type: str, object_key: str, **kwargs):
    args = [
        "prog",
        "--cycle-id",
        "cycle-002",
        "--device",
        "4WNET-MNS-KTG-RX",
        "--device-id",
        "1890",
        "--cycle-dir",
        str(cycle_dir),
        "--team",
        team,
        "--object-type",
        object_type,
        "--object-key",
        object_key,
        "--response-status",
        kwargs.pop("response_status", "answered"),
        "--owner",
        kwargs.pop("owner"),
        "--evidence",
        kwargs.pop("evidence"),
        "--notes",
        kwargs.pop("notes"),
        "--updated-by",
        kwargs.pop("updated_by", "uat"),
        "--output-dir",
        str(cycle_dir / "week1"),
    ]
    for key, value in kwargs.items():
        if value != "":
            flag = f"--{key.replace('_', '-')}"
            args.extend([flag, value])
    return args


def _seed(cycle_dir: Path, team: str, object_type: str, object_key: str, **kwargs) -> int:
    return run_main(seed_main, _seed_common_args(cycle_dir, team, object_type, object_key, **kwargs))


def test_01_seed_blocks_object_key_outside_scope() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        _copy_template(tmpdir)
        root = tmpdir / "reports" / "controlled-operation"
        cycle_dir = make_cycle(root)
        code = _seed(
            cycle_dir,
            "service",
            "subinterface",
            "not-in-scope",
            owner="UAT Service Owner",
            evidence="UAT evidence",
            notes="UAT response",
            tenant="Cliente Piloto",
            service_type="customer-internet",
            criticality="gold",
        )
        assert code != 0


def test_02_seed_blocks_secret_values() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        _copy_template(tmpdir)
        root = tmpdir / "reports" / "controlled-operation"
        cycle_dir = make_cycle(root)
        code = _seed(
            cycle_dir,
            "bgp",
            "bgp_peer",
            "203.0.113.1",
            owner="UAT BGP Owner",
            evidence="token=abc",
            notes="UAT response",
            remote_asn="65000",
            remote_bgp_group="UAT-GROUP",
            policy_intent="UAT policy intent",
            criticality="silver",
        )
        assert code != 0


def test_03_seed_creates_valid_local_response() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        _copy_template(tmpdir)
        root = tmpdir / "reports" / "controlled-operation"
        cycle_dir = make_cycle(root)
        code = _seed(
            cycle_dir,
            "service",
            "subinterface",
            "Eth-Trunk0.10",
            owner="UAT Service Owner",
            evidence="UAT evidence",
            notes="UAT response",
            tenant="Cliente Piloto",
            service_type="customer-internet",
            criticality="gold",
        )
        assert code == 0
        csv_path = cycle_dir / "week1" / "responses" / "service-team-response.csv"
        assert csv_path.exists()
        rows = csv_path.read_text(encoding="utf-8").splitlines()
        assert len(rows) >= 2


def test_04_seed_updates_duplicate_without_duplication() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        _copy_template(tmpdir)
        root = tmpdir / "reports" / "controlled-operation"
        cycle_dir = make_cycle(root)
        _seed(
            cycle_dir,
            "service",
            "subinterface",
            "Eth-Trunk0.10",
            owner="UAT Service Owner",
            evidence="UAT evidence 1",
            notes="UAT response 1",
            tenant="Cliente Piloto",
            service_type="customer-internet",
            criticality="gold",
        )
        _seed(
            cycle_dir,
            "service",
            "subinterface",
            "Eth-Trunk0.10",
            owner="UAT Service Owner",
            evidence="UAT evidence 2",
            notes="UAT response 2",
            tenant="Cliente Piloto",
            service_type="customer-internet",
            criticality="gold",
        )
        csv_path = cycle_dir / "week1" / "responses" / "service-team-response.csv"
        assert csv_path.exists()
        rows = csv_path.read_text(encoding="utf-8").splitlines()
        assert len(rows) == 2
        assert "UAT evidence 2" in rows[-1]


def test_05_reintake_moves_from_blocked_to_ready() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        _copy_template(tmpdir)
        root = tmpdir / "reports" / "controlled-operation"
        cycle_dir = make_cycle(root)
        _seed(
            cycle_dir,
            "service",
            "subinterface",
            "Eth-Trunk0.10",
            owner="UAT Service Owner",
            evidence="UAT evidence",
            notes="UAT response",
            tenant="Cliente Piloto",
            service_type="customer-internet",
            criticality="gold",
        )
        _seed(
            cycle_dir,
            "network_ops",
            "ip_address",
            "192.0.2.1/30",
            owner="UAT Network Ops",
            evidence="UAT evidence",
            notes="UAT response",
            interface="GigabitEthernet0/5/0",
            vrf="_public_",
            relation_type="infrastructure",
        )
        _seed(
            cycle_dir,
            "bgp",
            "bgp_peer",
            "203.0.113.1",
            owner="UAT BGP Owner",
            evidence="UAT evidence",
            notes="UAT response",
            remote_asn="65000",
            remote_bgp_group="UAT-GROUP",
            policy_intent="UAT policy intent",
            criticality="silver",
        )

        output = cycle_dir / "week1" / "CYCLE-002-WEEK1-INTAKE.md"
        output_json = cycle_dir / "week1" / "cycle-002-week1-intake.json"
        code = run_main(
            intake_main,
            [
                "prog",
                "--cycle-id",
                "cycle-002",
                "--device",
                "4WNET-MNS-KTG-RX",
                "--device-id",
                "1890",
                "--cycle-dir",
                str(cycle_dir),
                "--responses-dir",
                str(cycle_dir / "week1" / "responses"),
                "--output",
                str(output),
                "--output-json",
                str(output_json),
            ],
        )
        assert code == 0
        payload = json.loads(output_json.read_text(encoding="utf-8"))
        assert payload["decision"] == "WEEK1_INTAKE_READY"


def test_06_revalidation_accepts_valid_responses() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        _copy_template(tmpdir)
        root = tmpdir / "reports" / "controlled-operation"
        cycle_dir = make_cycle(root)
        for team, object_type, object_key, kwargs in [
            ("service", "subinterface", "Eth-Trunk0.10", {"tenant": "Cliente Piloto", "service_type": "customer-internet", "criticality": "gold"}),
            ("network_ops", "ip_address", "192.0.2.1/30", {"interface": "GigabitEthernet0/5/0", "vrf": "_public_", "relation_type": "infrastructure"}),
            ("bgp", "bgp_peer", "203.0.113.1", {"remote_asn": "65000", "remote_bgp_group": "UAT-GROUP", "policy_intent": "UAT policy intent", "criticality": "silver"}),
        ]:
            _seed(
                cycle_dir,
                team,
                object_type,
                object_key,
                owner="UAT Owner",
                evidence="UAT evidence",
                notes="UAT response",
                **kwargs,
            )

        output = cycle_dir / "week1" / "CYCLE-002-WEEK1-VALIDATION.md"
        output_json = cycle_dir / "week1" / "cycle-002-week1-validation.json"
        code = run_main(
            validate_main,
            [
                "prog",
                "--cycle-id",
                "cycle-002",
                "--device",
                "4WNET-MNS-KTG-RX",
                "--device-id",
                "1890",
                "--cycle-dir",
                str(cycle_dir),
                "--responses-dir",
                str(cycle_dir / "week1" / "responses"),
                "--policy-registry",
                str(ROOT / "policies" / "compliance"),
                "--output",
                str(output),
                "--output-json",
                str(output_json),
            ],
        )
        assert code == 0
        payload = json.loads(output_json.read_text(encoding="utf-8"))
        assert payload["decision"] in {"WEEK1_VALIDATION_PASSED", "WEEK1_VALIDATION_PASSED_WITH_RESTRICTIONS"}


def test_07_week2_prepare_creates_board_and_drafts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        _copy_template(tmpdir)
        root = tmpdir / "reports" / "controlled-operation"
        cycle_dir = make_cycle(root)
        for team, object_type, object_key, kwargs in [
            ("service", "subinterface", "Eth-Trunk0.10", {"tenant": "Cliente Piloto", "service_type": "customer-internet", "criticality": "gold"}),
            ("network_ops", "ip_address", "192.0.2.1/30", {"interface": "GigabitEthernet0/5/0", "vrf": "_public_", "relation_type": "infrastructure"}),
            ("bgp", "bgp_peer", "203.0.113.1", {"remote_asn": "65000", "remote_bgp_group": "UAT-GROUP", "policy_intent": "UAT policy intent", "criticality": "silver"}),
        ]:
            _seed(
                cycle_dir,
                team,
                object_type,
                object_key,
                owner="UAT Owner",
                evidence="UAT evidence",
                notes="UAT response",
                **kwargs,
            )

        validation_output = cycle_dir / "week1" / "CYCLE-002-WEEK1-VALIDATION.md"
        validation_json = cycle_dir / "week1" / "cycle-002-week1-validation.json"
        run_main(
            validate_main,
            [
                "prog",
                "--cycle-id",
                "cycle-002",
                "--device",
                "4WNET-MNS-KTG-RX",
                "--device-id",
                "1890",
                "--cycle-dir",
                str(cycle_dir),
                "--responses-dir",
                str(cycle_dir / "week1" / "responses"),
                "--policy-registry",
                str(ROOT / "policies" / "compliance"),
                "--output",
                str(validation_output),
                "--output-json",
                str(validation_json),
            ],
        )

        output_dir = cycle_dir / "week2"
        code = run_main(
            week2_prepare_main,
            [
                "prog",
                "--cycle-id",
                "cycle-002",
                "--device",
                "4WNET-MNS-KTG-RX",
                "--device-id",
                "1890",
                "--cycle-dir",
                str(cycle_dir),
                "--week1-validation",
                str(validation_json),
                "--output-dir",
                str(output_dir),
            ],
        )
        assert code == 0
        assert (output_dir / "CYCLE-002-WEEK2-REVIEW-BOARD.md").exists()
        assert (output_dir / "CYCLE-002-WEEK2-DECISIONS.csv").exists()
        assert (output_dir / "approval-drafts").exists()


def test_08_week2_prepare_blocks_without_ready_items() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        _copy_template(tmpdir)
        root = tmpdir / "reports" / "controlled-operation"
        cycle_dir = make_cycle(root)
        validation_json = cycle_dir / "week1" / "cycle-002-week1-validation.json"
        validation_json.parent.mkdir(parents=True, exist_ok=True)
        validation_json.write_text(
            json.dumps({"decision": "WEEK1_VALIDATION_BLOCKED", "summary": {"validated": 0, "still_pending": 3, "needs_clarification": 0, "blocked": 0, "rejected": 0}, "ready_for_week2_review": []}),
            encoding="utf-8",
        )
        output_dir = cycle_dir / "week2"
        code = run_main(
            week2_prepare_main,
            [
                "prog",
                "--cycle-id",
                "cycle-002",
                "--device",
                "4WNET-MNS-KTG-RX",
                "--device-id",
                "1890",
                "--cycle-dir",
                str(cycle_dir),
                "--week1-validation",
                str(validation_json),
                "--output-dir",
                str(output_dir),
            ],
        )
        assert code != 0


def test_09_webui_week1_pending_and_week2_routes_200() -> None:
    with ASGIClient() as client:
        assert client.get("/controlled-operation/cycle-002/week1/pending").status_code == 200
        assert client.get("/controlled-operation/cycle-002/week2").status_code == 200


def test_10_webui_routes_do_not_show_apply_sync_token() -> None:
    with ASGIClient() as client:
        for path in [
            "/controlled-operation/cycle-002/week1/pending",
            "/controlled-operation/cycle-002/week2",
        ]:
            response = client.get(path)
            lowered = response.text.lower()
            assert "apply" not in lowered
            assert "sync" not in lowered
            assert "token" not in lowered


def test_11_no_netbox_write_keywords_in_outputs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        _copy_template(tmpdir)
        root = tmpdir / "reports" / "controlled-operation"
        cycle_dir = make_cycle(root)
        _seed(
            cycle_dir,
            "service",
            "subinterface",
            "Eth-Trunk0.10",
            owner="UAT Service Owner",
            evidence="UAT evidence",
            notes="UAT response",
            tenant="Cliente Piloto",
            service_type="customer-internet",
            criticality="gold",
        )
        report = cycle_dir / "week1" / "CYCLE-002-WEEK1-RESPONSE-SEED.md"
        assert report.exists()
        lowered = report.read_text(encoding="utf-8").lower()
        assert "netbox write" not in lowered
        assert "approvalrecord" not in lowered
        assert "applyplan" not in lowered


def main() -> int:
    tests = [
        test_01_seed_blocks_object_key_outside_scope,
        test_02_seed_blocks_secret_values,
        test_03_seed_creates_valid_local_response,
        test_04_seed_updates_duplicate_without_duplication,
        test_05_reintake_moves_from_blocked_to_ready,
        test_06_revalidation_accepts_valid_responses,
        test_07_week2_prepare_creates_board_and_drafts,
        test_08_week2_prepare_blocks_without_ready_items,
        test_09_webui_week1_pending_and_week2_routes_200,
        test_10_webui_routes_do_not_show_apply_sync_token,
        test_11_no_netbox_write_keywords_in_outputs,
    ]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"✓ {test.__name__}")
        except Exception as exc:
            failed += 1
            print(f"✗ {test.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} tests passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
