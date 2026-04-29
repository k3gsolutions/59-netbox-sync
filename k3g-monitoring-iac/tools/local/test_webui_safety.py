#!/usr/bin/env python3
"""Security and behavior checks for the local pending-item Web UI."""

from __future__ import annotations

import csv
import json
import tempfile
import shutil
import socket
import subprocess
import time
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from urllib import error, request as urllib_request

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from webui.app import app
from webui.services.response_forms import load_pending_items, _extract_text_values, validate_response_payload
from webui.services.artifact_scanner import safe_resolve_path
from tools.local.validate_week1_responses import validate_response


ROOT = Path(__file__).parent.parent.parent
REPORTS_ROOT = ROOT / "reports" / "pilot-device-compliance"
RESPONSES_DIR = REPORTS_ROOT / "week1-responses"
SERVER_PORT = 8910
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"

try:
    from fastapi.testclient import TestClient  # type: ignore
except Exception:
    TestClient = None


class LocalHttpClient:
    def __init__(self):
        self.proc = None

    def __enter__(self):
        if TestClient is not None:
            self.client = TestClient(app)
            return self.client

        self.proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "webui.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(SERVER_PORT),
                "--log-level",
                "error",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", SERVER_PORT), timeout=0.2):
                    break
            except OSError:
                time.sleep(0.2)
        else:
            raise RuntimeError("uvicorn server did not start")
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()
            self.proc = None

    def _request(self, method: str, path: str, json_body: Dict[str, object] | None = None):
        if TestClient is not None:
            raise RuntimeError("TestClient path should not call LocalHttpClient._request")

        url = SERVER_URL + path
        headers = {}
        data = None
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"
            headers["Accept"] = "application/json"

        req = urllib_request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib_request.urlopen(req, timeout=20) as resp:
                body = resp.read().decode("utf-8")
                return SimpleResponse(resp.status, body)
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            return SimpleResponse(exc.code, body)

    def get(self, path: str):
        if TestClient is not None:
            return self.client.get(path)
        return self._request("GET", path)

    def post(self, path: str, json: Dict[str, object] | None = None):
        if TestClient is not None:
            return self.client.post(path, json=json)
        return self._request("POST", path, json_body=json)


class SimpleResponse:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text

    def json(self):
        return json.loads(self.text)


def _backup_response_artifacts() -> Dict[Path, str | None]:
    backups: Dict[Path, str | None] = {}
    for path in [
        RESPONSES_DIR / "service-team-response.csv",
        RESPONSES_DIR / "network-ops-response.csv",
        RESPONSES_DIR / "bgp-team-response.csv",
        RESPONSES_DIR / "audit" / "service-team-response-audit.json",
        RESPONSES_DIR / "audit" / "network-ops-response-audit.json",
        RESPONSES_DIR / "audit" / "bgp-team-response-audit.json",
    ]:
        if path.exists():
            backups[path] = path.read_text(encoding="utf-8")
        else:
            backups[path] = None
    return backups


def _restore_response_artifacts(backups: Dict[Path, str | None]) -> None:
    for path, content in backups.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if content is None:
            if path.exists():
                path.unlink()
        else:
            path.write_text(content, encoding="utf-8")


def _clean_response_artifacts() -> None:
    if RESPONSES_DIR.exists():
        shutil.rmtree(RESPONSES_DIR)
    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
    (RESPONSES_DIR / "audit").mkdir(parents=True, exist_ok=True)


def _client() -> TestClient:
    return LocalHttpClient()


def _first_item(team_slug: str) -> Dict[str, object]:
    items = load_pending_items("4WNET-MNS-KTG-RX")
    for item in items:
        if item.get("responsible_team_slug") == team_slug:
            return item
    raise RuntimeError(f"no item found for {team_slug}")


def _post_response(client: TestClient, item: Dict[str, object], payload: Dict[str, object]):
    url = f"/service-engagement/4WNET-MNS-KTG-RX/pending-items/{item['safe_item_id']}/response"
    body = dict(payload)
    body.setdefault("safe_item_id", item["safe_item_id"])
    body.setdefault("updated_by", "webui-tester")
    return client.post(url, json=body)


def _build_valid_payload(item: Dict[str, object], updated_by: str = "uat") -> Dict[str, object]:
    object_type = str(item.get("object_type", "")).lower()
    if object_type == "subinterface":
        return {
            "status": "answered",
            "tenant": "UAT Cliente Teste",
            "service_type": "customer-internet",
            "criticality": "gold",
            "owner": "UAT Service Owner",
            "evidence": "UAT evidence service contract reference",
            "notes": "UAT service team response",
            "updated_by": updated_by,
        }
    if object_type == "ip_address":
        return {
            "status": "answered",
            "interface": "GigabitEthernet0/5/0",
            "vrf": "_public_",
            "relation_type": "infrastructure",
            "owner": "UAT Network Ops",
            "evidence": "UAT evidence IP detected on interface",
            "notes": "UAT network ops response",
            "updated_by": updated_by,
        }
    return {
        "status": "answered",
        "remote_asn": "65000",
        "remote_bgp_group": "UAT-GROUP",
        "policy_intent": "UAT policy intent for peer validation",
        "criticality": "silver",
        "owner": "UAT BGP Owner",
        "evidence": "UAT evidence BGP peer documentation",
        "notes": "UAT BGP response",
        "updated_by": updated_by,
    }


def _fill_all_responses(client: TestClient) -> None:
    for item in load_pending_items("4WNET-MNS-KTG-RX"):
        if item.get("current_status") == "answered":
            continue
        _post_response(client, item, _build_valid_payload(item))


def _run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_imports() -> bool:
    print("Test 1: Imports")
    try:
        from webui import app as _  # noqa: F401
        print("  ✓ app imports OK")
        return True
    except Exception as exc:
        print(f"  ✗ FAILED: {exc}")
        return False


def test_pending_items_get() -> bool:
    print("\nTest 2: GET pending-items")
    with _client() as client:
        response = client.get("/service-engagement/4WNET-MNS-KTG-RX/pending-items")
        if response.status_code != 200:
            print(f"  ✗ FAILED: status={response.status_code}")
            return False
        if "Pending Items" not in response.text:
            print("  ✗ FAILED: HTML body missing title")
            return False
    print("  ✓ GET pending-items returns 200")
    return True


def test_get_valid_item() -> bool:
    print("\nTest 3: GET valid item")
    item = _first_item("service-team")
    with _client() as client:
        response = client.get(f"/service-engagement/4WNET-MNS-KTG-RX/pending-items/{item['safe_item_id']}")
        data = response.json()
        if response.status_code != 200 or not data.get("success"):
            print(f"  ✗ FAILED: status={response.status_code}, body={data}")
            return False
        if "schema" not in data or "item" not in data:
            print("  ✗ FAILED: missing item/schema")
            return False
    print("  ✓ GET valid item returns schema")
    return True


def test_get_invalid_item() -> bool:
    print("\nTest 4: GET invalid item")
    with _client() as client:
        response = client.get("/service-engagement/4WNET-MNS-KTG-RX/pending-items/not-a-real-id")
        if response.status_code != 404:
            print(f"  ✗ FAILED: status={response.status_code}")
            return False
    print("  ✓ GET invalid item returns 404")
    return True


def test_post_service_team_valid() -> bool:
    print("\nTest 5: POST valid service-team")
    item = _first_item("service-team")
    with _client() as client:
        response = _post_response(
            client,
            item,
            {
                "status": "answered",
                "tenant": "customer-a",
                "service_type": "customer-internet",
                "criticality": "gold",
                "owner": "noc-team",
                "evidence": "Ticket #1001",
            },
        )
        if response.status_code != 200:
            print(f"  ✗ FAILED: status={response.status_code}, body={response.text}")
            return False
        data = response.json()
        if not data.get("success") or "pipeline" not in data or not Path(ROOT / data["csv_path"]).exists():
            print(f"  ✗ FAILED: body={data}")
            return False
    print("  ✓ service-team CSV saved")
    return True


def test_post_network_ops_valid() -> bool:
    print("\nTest 6: POST valid network-ops")
    item = _first_item("network-ops")
    with _client() as client:
        response = _post_response(
            client,
            item,
            {
                "status": "answered",
                "interface": "GigabitEthernet0/5/0",
                "vrf": "default",
                "relation_type": "infrastructure",
                "service_relation": "customer-a",
                "owner": "netops",
                "evidence": "NMS snapshot",
            },
        )
        if response.status_code != 200:
            print(f"  ✗ FAILED: status={response.status_code}, body={response.text}")
            return False
    print("  ✓ network-ops CSV saved")
    return True


def test_post_bgp_valid() -> bool:
    print("\nTest 7: POST valid bgp-team")
    item = _first_item("bgp-team")
    with _client() as client:
        response = _post_response(
            client,
            item,
            {
                "status": "answered",
                "remote_asn": "64512",
                "remote_bgp_group": "isp-uplink",
                "policy_intent": "Prefer local primary path",
                "owner": "bgp-team",
                "criticality": "platinum",
                "evidence": "Peer config snapshot",
            },
        )
        if response.status_code != 200:
            print(f"  ✗ FAILED: status={response.status_code}, body={response.text}")
            return False
    print("  ✓ bgp-team CSV saved")
    return True


def test_invalid_service_type() -> bool:
    print("\nTest 8: Invalid service_type")
    item = _first_item("service-team")
    with _client() as client:
        response = _post_response(
            client,
            item,
            {
                "status": "answered",
                "tenant": "customer-a",
                "service_type": "invalid-service",
                "criticality": "gold",
                "owner": "noc-team",
                "evidence": "Ticket #1001",
            },
        )
        if response.status_code == 200:
            print("  ✗ FAILED: invalid service_type accepted")
            return False
    print("  ✓ invalid service_type rejected")
    return True


def test_invalid_criticality() -> bool:
    print("\nTest 9: Invalid criticality")
    item = _first_item("service-team")
    with _client() as client:
        response = _post_response(
            client,
            item,
            {
                "status": "answered",
                "tenant": "customer-a",
                "service_type": "customer-internet",
                "criticality": "diamond",
                "owner": "noc-team",
                "evidence": "Ticket #1001",
            },
        )
        if response.status_code == 200:
            print("  ✗ FAILED: invalid criticality accepted")
            return False
    print("  ✓ invalid criticality rejected")
    return True


def test_invalid_asn() -> bool:
    print("\nTest 10: Invalid remote_asn")
    item = _first_item("bgp-team")
    with _client() as client:
        response = _post_response(
            client,
            item,
            {
                "status": "answered",
                "remote_asn": "5000000000",
                "remote_bgp_group": "isp-uplink",
                "policy_intent": "Prefer local primary path",
                "owner": "bgp-team",
                "criticality": "platinum",
                "evidence": "Peer config snapshot",
            },
        )
        if response.status_code == 200:
            print("  ✗ FAILED: invalid ASN accepted")
            return False
    print("  ✓ invalid ASN rejected")
    return True


def test_object_key_traversal_blocked() -> bool:
    print("\nTest 11: Path traversal in object_key")
    item = _first_item("service-team")
    with _client() as client:
        response = client.post(
            f"/service-engagement/4WNET-MNS-KTG-RX/pending-items/{item['safe_item_id']}/response",
            json={
                "safe_item_id": item["safe_item_id"],
                "object_key": "../evil",
                "status": "answered",
                "updated_by": "webui-tester",
            },
        )
        if response.status_code == 200:
            print("  ✗ FAILED: traversal accepted")
            return False
    print("  ✓ traversal blocked")
    return True


def test_secret_blocked() -> bool:
    print("\nTest 12: Secret keywords blocked")
    item = _first_item("service-team")
    with _client() as client:
        response = _post_response(
            client,
            item,
            {
                "status": "answered",
                "tenant": "token-secret",
                "service_type": "customer-internet",
                "criticality": "gold",
                "owner": "noc-team",
                "evidence": "Ticket #1001",
            },
        )
        if response.status_code == 200:
            print("  ✗ FAILED: secret value accepted")
            return False
    print("  ✓ secret value rejected")
    return True


def test_download_csv_allowed() -> bool:
    print("\nTest 13: CSV download allowed")
    csv_path = RESPONSES_DIR / "bgp-team-response.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_text(
        "\n".join([
            "device,object_type,object_key,responsible_team,status,tenant,service_type,criticality,owner,evidence,interface,vrf,service_relation,remote_asn,remote_bgp_group,policy_intent,notes,updated_at,updated_by,relation_type",
            "4WNET-MNS-KTG-RX,bgp_peer,TEST-BGP,bgp-team,answered,,,,Test Operator,Test evidence,,,,65000,TEST-GROUP,Test policy intent,uat,2026-04-29T00:00:00Z,uat,",
        ]) + "\n",
        encoding="utf-8",
    )
    with _client() as client:
        response = client.get("/reports/download?path=pilot-device-compliance/week1-responses/bgp-team-response.csv")
        if response.status_code != 200:
            print(f"  ✗ FAILED: status={response.status_code}, body={response.text}")
            return False
        if "TEST-BGP" not in response.text:
            print("  ✗ FAILED: CSV body missing expected content")
            return False
    print("  ✓ CSV download allowed")
    return True


def test_download_csv_allowed_reports_prefix() -> bool:
    print("\nTest 14: CSV download allowed with reports/ prefix")
    with _client() as client:
        response = client.get("/reports/download?path=reports/pilot-device-compliance/week1-responses/bgp-team-response.csv")
        if response.status_code != 200:
            print(f"  ✗ FAILED: status={response.status_code}, body={response.text}")
            return False
    print("  ✓ CSV download allowed with reports/ prefix")
    return True


def test_download_sensitive_blocked() -> bool:
    print("\nTest 15: Sensitive download blocked")
    blocked_paths = [
        "/reports/download?path=payload.local.json",
        "/reports/download?path=pilot-device-compliance/payload.local.json",
        "/reports/download?path=../../etc/passwd",
    ]
    with _client() as client:
        for path in blocked_paths:
            response = client.get(path)
            if response.status_code == 200:
                print(f"  ✗ FAILED: blocked path allowed: {path}")
                return False
    print("  ✓ sensitive paths blocked")
    return True


def test_ip_detection_helpers() -> bool:
    print("\nTest 16: IP detection helpers")
    info = _extract_text_values("assigned_interface=GigabitEthernet0/5/0 vrf=default")
    if info.get("detected_interface") != "GigabitEthernet0/5/0" or info.get("detected_vrf") != "default":
        print(f"  ✗ FAILED: detection mismatch: {info}")
        return False
    if info.get("status_hint") != "confirm_detected_mapping":
        print(f"  ✗ FAILED: status_hint mismatch: {info}")
        return False
    print("  ✓ detection helpers extract interface/vrf")
    return True


def test_ip_validate_with_detected_mapping() -> bool:
    print("\nTest 17: IP validation with detected mapping")
    item = {
        "object_type": "ip_address",
        "object_key": "192.0.2.1/30",
        "responsible_team": "Network Ops",
        "detected_interface": "GigabitEthernet0/5/0",
        "detected_vrf": "default",
    }
    payload = {
        "status": "answered",
        "relation_type": "infrastructure",
        "owner": "netops",
        "evidence": "UAT evidence mapping confirmed",
        "updated_by": "uat",
    }
    valid, errors = validate_response_payload(item, payload)
    if not valid or errors:
        print(f"  ✗ FAILED: expected valid, got {errors}")
        return False
    print("  ✓ IP validation accepts detected mapping")
    return True


def test_ip_validate_service_relation_required() -> bool:
    print("\nTest 18: IP validation relation_type=service")
    item = {
        "object_type": "ip_address",
        "object_key": "192.0.2.1/30",
        "responsible_team": "Network Ops",
    }
    payload = {
        "status": "answered",
        "relation_type": "service",
        "owner": "netops",
        "evidence": "UAT",
        "interface": "GigabitEthernet0/5/0",
        "vrf": "default",
        "updated_by": "uat",
    }
    valid, errors = validate_response_payload(item, payload)
    if valid or not any("service_relation" in err for err in errors):
        print(f"  ✗ FAILED: expected service_relation error, got {errors}")
        return False
    print("  ✓ IP validation requires service_relation for service relation_type")
    return True


def test_week1_validation_accepts_relation_type() -> bool:
    print("\nTest 19: Week1 validation accepts relation_type")
    item = {
        "object_type": "ip_address",
        "object_key": "192.0.2.1/30",
        "responsible_team": "network-ops",
    }
    response = {
        "status": "answered",
        "relation_type": "infrastructure",
        "owner": "netops",
        "evidence": "UAT",
        "interface": "GigabitEthernet0/5/0",
        "vrf": "default",
        "updated_by": "uat",
    }
    status, reason = validate_response(item, response)
    if status != "validated":
        print(f"  ✗ FAILED: status={status}, reason={reason}")
        return False
    print("  ✓ week1 validator accepts relation_type")
    return True


def test_csv_header() -> bool:
    print("\nTest 20: CSV header")
    csv_path = RESPONSES_DIR / "service-team-response.csv"
    if not csv_path.exists():
        print("  ✗ FAILED: CSV missing")
        return False
    with csv_path.open("r", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
    expected = [
        "device",
        "object_type",
        "object_key",
        "responsible_team",
        "status",
        "tenant",
        "service_type",
        "criticality",
        "owner",
        "evidence",
        "interface",
        "vrf",
        "service_relation",
        "remote_asn",
        "remote_bgp_group",
        "policy_intent",
        "notes",
        "updated_at",
        "updated_by",
        "relation_type",
    ]
    if header != expected:
        print(f"  ✗ FAILED: header mismatch\n  got={header}")
        return False
    print("  ✓ CSV header matches")
    return True


def test_update_same_object_key() -> bool:
    print("\nTest 21: Update same object_key without duplicates")
    item = _first_item("service-team")
    with _client() as client:
        first = _post_response(
            client,
            item,
            {
                "status": "answered",
                "tenant": "customer-a",
                "service_type": "customer-internet",
                "criticality": "gold",
                "owner": "noc-team",
                "evidence": "Ticket #2001",
            },
        )
        second = _post_response(
            client,
            item,
            {
                "status": "needs_clarification",
                "notes": "Need more evidence",
            },
        )
        if first.status_code != 200 or second.status_code != 200:
            print(f"  ✗ FAILED: first={first.status_code}, second={second.status_code}")
            return False

    csv_path = RESPONSES_DIR / "service-team-response.csv"
    with csv_path.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    matches = [row for row in rows if row.get("object_key") == item["object_key"]]
    if len(matches) != 1:
        print(f"  ✗ FAILED: expected 1 row, got {len(matches)}")
        return False
    if matches[0].get("status") != "needs_clarification":
        print(f"  ✗ FAILED: status not updated: {matches[0].get('status')}")
        return False
    print("  ✓ object_key updated in place")
    return True


def test_audit_created() -> bool:
    print("\nTest 22: Audit JSON")
    audit_path = RESPONSES_DIR / "audit" / "service-team-response-audit.json"
    if not audit_path.exists():
        print("  ✗ FAILED: audit missing")
        return False
    data = json.loads(audit_path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        print("  ✗ FAILED: audit empty")
        return False
    print("  ✓ audit JSON created")
    return True


def test_modal_buttons_present() -> bool:
    print("\nTest 23: Modal buttons present")
    modal = ROOT / "webui" / "templates" / "partials" / "pending_item_modal.html"
    content = modal.read_text(encoding="utf-8")
    if "Salvar e fechar" not in content or ">Salvar<" not in content:
        print("  ✗ FAILED: save buttons not found")
        return False
    print("  ✓ modal buttons present")
    return True


def test_run_validation_endpoint() -> bool:
    print("\nTest 24: Run validation endpoint")
    with _client() as client:
        response = client.post("/service-engagement/4WNET-MNS-KTG-RX/responses/run-validation", json={})
        data = response.json()
        if response.status_code != 200 or not data.get("success"):
            print(f"  ✗ FAILED: status={response.status_code}, body={data}")
            return False
        if "validation" not in data or "week2_gate" not in data:
            print(f"  ✗ FAILED: missing summary fields: {data}")
            return False
    print("  ✓ run-validation returns summary")
    return True


def test_finalize_with_restrictions() -> bool:
    print("\nTest 25: Finalize with restrictions")
    with _client() as client:
        response = client.post("/service-engagement/4WNET-MNS-KTG-RX/responses/finalize", json={})
        data = response.json()
        if response.status_code != 200 or not data.get("success"):
            print(f"  ✗ FAILED: status={response.status_code}, body={data}")
            return False
        if data.get("week2_gate") not in {"GO_WITH_RESTRICTIONS", "NO_GO"}:
            print(f"  ✗ FAILED: gate={data.get('week2_gate')}")
            return False
    print("  ✓ finalize handles restrictions")
    return True


def test_finalize_when_complete() -> bool:
    print("\nTest 26: Finalize when complete")
    with _client() as client:
        _fill_all_responses(client)
        response = client.post("/service-engagement/4WNET-MNS-KTG-RX/responses/finalize", json={})
        data = response.json()
        if response.status_code != 200 or not data.get("success"):
            print(f"  ✗ FAILED: status={response.status_code}, body={data}")
            return False
        if data.get("week2_gate") != "GO_WEEK2_REVIEW" or not data.get("week2_prepared"):
            print(f"  ✗ FAILED: gate={data.get('week2_gate')}, prepared={data.get('week2_prepared')}")
            return False
    week2_board = REPORTS_ROOT / "week2-review" / "week2-review-board.md"
    if not week2_board.exists():
        print("  ✗ FAILED: week2 board missing")
        return False
    print("  ✓ finalize prepares Week 2 when complete")
    return True


def test_validation_dashboard() -> bool:
    print("\nTest 27: Validation dashboard")
    with _client() as client:
        response = client.get("/service-engagement/4WNET-MNS-KTG-RX/validation")
        if response.status_code != 200:
            print(f"  ✗ FAILED: status={response.status_code}")
            return False
    template = ROOT / "webui" / "templates" / "service_engagement_validation.html"
    content = template.read_text(encoding="utf-8")
    for needle in ["Validadas", "Ainda pendentes", "Finalizar respostas e preparar Week 2", "validation-count-validated"]:
        if needle not in content:
            print(f"  ✗ FAILED: missing {needle}")
            return False
    print("  ✓ validation dashboard present")
    return True


def test_week2_review_pages() -> bool:
    print("\nTest 28: Week 2 review pages")
    with _client() as client:
        review = client.get("/service-engagement/4WNET-MNS-KTG-RX/week2-review")
        drafts = client.get("/service-engagement/4WNET-MNS-KTG-RX/approval-drafts")
        queue = client.get("/approval-queue")
        if review.status_code != 200 or drafts.status_code != 200 or queue.status_code != 200:
            print(f"  ✗ FAILED: review={review.status_code}, drafts={drafts.status_code}, queue={queue.status_code}")
            return False
    review_template = ROOT / "webui" / "templates" / "week2_review.html"
    drafts_template = ROOT / "webui" / "templates" / "approval_drafts.html"
    queue_template = ROOT / "webui" / "templates" / "approval_queue.html"
    if "Critério de liberação da Semana 2" not in review_template.read_text(encoding="utf-8"):
        print("  ✗ FAILED: review page missing gate card")
        return False
    if "Rascunhos não são aprovações" not in drafts_template.read_text(encoding="utf-8"):
        print("  ✗ FAILED: drafts page missing review note")
        return False
    if "Registros de Aprovação Propostos" not in queue_template.read_text(encoding="utf-8"):
        print("  ✗ FAILED: queue missing proposed approvals section")
        return False
    print("  ✓ week 2 review pages present")
    return True


def test_week2_decision_validation_script() -> bool:
    print("\nTest 29: Week 2 decision validation script")
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        drafts_dir = root / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        draft = {
            "draft_id": "draft-1",
            "status": "draft_review",
            "device": "4WNET-MNS-KTG-RX",
            "device_id": 1890,
            "object_type": "subinterface",
            "object_key": "Eth-Trunk0.147",
            "action": "safe_create_staged",
            "category": "service_candidate",
            "created_at": "2026-04-29T00:00:00Z",
            "allowed_to_promote": False,
            "safety": {"no_netbox_write": True, "no_apply_plan_created": True, "manual_review_required": True},
        }
        (drafts_dir / "approval-draft-Eth-Trunk0-147.json").write_text(json.dumps(draft), encoding="utf-8")
        decisions = root / "week2-review-decisions.csv"
        decisions.write_text(
            "device,device_id,object_type,object_key,responsible_team,tenant,service_type,criticality,owner,reviewer,decision,reason,notes,reviewed_at,approval_record_allowed\n"
            "4WNET-MNS-KTG-RX,1890,subinterface,Eth-Trunk0.147,service team,UAT Cliente Teste,customer-internet,gold,UAT Owner,reviewer-qa,request_changes,Precisa ajuste,UAT note,2026-04-29T00:00:00Z,\n",
            encoding="utf-8",
        )
        output = root / "week2-review-decision-validation.md"
        proc = _run_script(
            "tools/local/validate_week2_review_decisions.py",
            "--decisions",
            str(decisions),
            "--drafts-dir",
            str(drafts_dir),
            "--output",
            str(output),
            "--device",
            "4WNET-MNS-KTG-RX",
        )
        if proc.returncode != 0 or not output.exists():
            print(f"  ✗ FAILED: rc={proc.returncode}, stdout={proc.stdout}, stderr={proc.stderr}")
            return False
        human_report = root / "WEEK2-HUMAN-REVIEW-EXECUTION.md"
        if not human_report.exists():
            print("  ✗ FAILED: human report missing")
            return False
        if (root / "promoted").exists():
            print("  ✗ FAILED: validation script should not promote anything")
            return False
    print("  ✓ validation script reports without promoting")
    return True


def test_week2_promotion_script_only_promotes_approved() -> bool:
    print("\nTest 30: Week 2 promotion script only promotes approved")
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        drafts_dir = root / "week2-approval-drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        draft = {
            "draft_id": "draft-2",
            "status": "draft_review",
            "device": "4WNET-MNS-KTG-RX",
            "device_id": 1890,
            "object_type": "bgp_peer",
            "object_key": "203.0.113.1",
            "action": "safe_create_staged",
            "category": "service_candidate",
            "created_at": "2026-04-29T00:00:00Z",
            "allowed_to_promote": False,
            "safety": {"no_netbox_write": True, "no_apply_plan_created": True, "manual_review_required": True},
        }
        (drafts_dir / "approval-draft-203-0-113-1.json").write_text(json.dumps(draft), encoding="utf-8")
        decisions = root / "week2-review-decisions.csv"
        decisions.write_text(
            "device,device_id,object_type,object_key,responsible_team,tenant,service_type,criticality,owner,reviewer,decision,reason,notes,reviewed_at,approval_record_allowed\n"
            "4WNET-MNS-KTG-RX,1890,bgp_peer,203.0.113.1,bgp team,,,,UAT Owner,reviewer-qa,approve_for_approval_record,OK,UAT approved,2026-04-29T00:00:00Z,true\n"
            "4WNET-MNS-KTG-RX,1890,bgp_peer,203.0.113.1,bgp team,,,,UAT Owner,reviewer-qa,request_changes,Need more data,UAT note,2026-04-29T00:00:00Z,\n",
            encoding="utf-8",
        )
        out_dir = root / "approvals"
        proc = _run_script(
            "tools/local/promote_week2_drafts_to_approvals.py",
            "--device",
            "4WNET-MNS-KTG-RX",
            "--device-id",
            "1890",
            "--drafts-dir",
            str(drafts_dir),
            "--decisions",
            str(decisions),
            "--output-dir",
            str(out_dir),
        )
        promoted = list((out_dir / "promoted").glob("approval-record-*.json"))
        if proc.returncode != 0 or len(promoted) != 1:
            print(f"  ✗ FAILED: rc={proc.returncode}, promoted={len(promoted)}, stdout={proc.stdout}, stderr={proc.stderr}")
            return False
        data = json.loads(promoted[0].read_text(encoding="utf-8"))
        if data.get("status") != "proposed":
            print(f"  ✗ FAILED: status={data.get('status')}")
            return False
        if data.get("review", {}).get("status") != "proposed":
            print(f"  ✗ FAILED: review status={data.get('review', {}).get('status')}")
            return False
        if data.get("safety", {}).get("no_apply_plan_created") is not True:
            print("  ✗ FAILED: safety flag missing")
            return False
    print("  ✓ promotion script promotes only approved rows")
    return True


def test_week2_queue_has_proposed_approvals() -> bool:
    print("\nTest 31: Week 2 queue has proposed approvals")
    with _client() as client:
        response = client.get("/approval-queue")
        if response.status_code != 200:
            print(f"  ✗ FAILED: status={response.status_code}")
            return False
    queue_template = ROOT / "webui" / "templates" / "approval_queue.html"
    if "Registros de Aprovação Propostos" not in queue_template.read_text(encoding="utf-8"):
        print("  ✗ FAILED: proposed approvals section missing")
        return False
    print("  ✓ queue shows proposed approvals")
    return True


def test_uat_report_script() -> bool:
    print("\nTest 32: UAT report script")
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "WEEK1-UAT-RESPONSE-AUDIT.test.md"
        proc = _run_script(
            "tools/local/manage_week1_uat_responses.py",
            "--responses-dir",
            str(RESPONSES_DIR),
            "--mode",
            "report",
            "--output",
            str(out),
        )
        if proc.returncode != 0 or not out.exists():
            print(f"  ✗ FAILED: rc={proc.returncode}, stdout={proc.stdout}, stderr={proc.stderr}")
            return False
    print("  ✓ UAT report script works")
    return True


def test_uat_archive_preserves_audit() -> bool:
    print("\nTest 33: UAT archive preserves audit")
    with tempfile.TemporaryDirectory() as tmpdir:
        responses = Path(tmpdir) / "week1-responses"
        audit = responses / "audit"
        audit.mkdir(parents=True, exist_ok=True)
        (responses / "service-team-response.csv").write_text(
            "device,object_type,object_key,responsible_team,status,tenant,service_type,criticality,owner,evidence,interface,vrf,service_relation,remote_asn,remote_bgp_group,policy_intent,notes,updated_at,updated_by,relation_type\n"
            "4WNET-MNS-KTG-RX,subinterface,TEST-UAT,Service Team,answered,UAT,customer-internet,gold,UAT Owner,UAT evidence,,,,,,,UAT note,2026-04-29T00:00:00Z,uat,\n",
            encoding="utf-8",
        )
        (audit / "service-team-response-audit.json").write_text(
            '[{"updated_by":"uat","object_key":"TEST-UAT"}]',
            encoding="utf-8",
        )
        proc = _run_script(
            "tools/local/manage_week1_uat_responses.py",
            "--responses-dir",
            str(responses),
            "--mode",
            "archive",
            "--confirm-archive-uat",
            "--output",
            str(Path(tmpdir) / "audit.md"),
        )
        if proc.returncode != 0:
            print(f"  ✗ FAILED: rc={proc.returncode}, stdout={proc.stdout}, stderr={proc.stderr}")
            return False
        archive_root = responses / "uat-archive"
        archived_csv = list(archive_root.rglob("service-team-response.csv"))
        archived_audit = list(archive_root.rglob("service-team-response-audit.json"))
        if not archived_csv or not archived_audit:
            print("  ✗ FAILED: archive missing csv or audit")
            return False
    print("  ✓ UAT archive preserves audit")
    return True


def test_uat_reset_requires_confirmation() -> bool:
    print("\nTest 34: UAT reset requires confirmation")
    proc = _run_script(
        "tools/local/manage_week1_uat_responses.py",
        "--responses-dir",
        str(RESPONSES_DIR),
        "--mode",
        "reset",
    )
    if proc.returncode == 0:
        print("  ✗ FAILED: reset succeeded without confirmation")
        return False
    print("  ✓ reset blocked without confirmation")
    return True


def test_uat_keep_as_real_requires_confirmation() -> bool:
    print("\nTest 35: keep-as-real requires confirmation")
    proc = _run_script(
        "tools/local/manage_week1_uat_responses.py",
        "--responses-dir",
        str(RESPONSES_DIR),
        "--mode",
        "keep-as-real",
    )
    if proc.returncode == 0:
        print("  ✗ FAILED: keep-as-real succeeded without confirmation")
        return False
    print("  ✓ keep-as-real blocked without confirmation")
    return True


def test_no_netbox_write() -> bool:
    print("\nTest 36: No NetBox write")
    app_file = ROOT / "webui" / "app.py"
    content = app_file.read_text(encoding="utf-8")
    forbidden = ["netbox_write", "NETBOX_WRITE_TOKEN", "apply_to_netbox"]
    if any(term in content for term in forbidden):
        print("  ✗ FAILED: NetBox write keyword found")
        return False
    print("  ✓ no NetBox write keyword found")
    return True


def test_no_applyplan() -> bool:
    print("\nTest 37: No ApplyPlan automatic")
    app_file = ROOT / "webui" / "app.py"
    content = app_file.read_text(encoding="utf-8")
    if "ApplyPlan(" in content:
        print("  ✗ FAILED: ApplyPlan reference found")
        return False
    print("  ✓ no ApplyPlan auto-creation")
    return True


def test_no_approvalrecord() -> bool:
    print("\nTest 38: No ApprovalRecord automatic")
    app_file = ROOT / "webui" / "app.py"
    content = app_file.read_text(encoding="utf-8")
    if "ApprovalRecord(" in content:
        print("  ✗ FAILED: ApprovalRecord reference found")
        return False
    print("  ✓ no ApprovalRecord auto-creation")
    return True


def test_no_apply_sync_routes() -> bool:
    print("\nTest 39: No apply/sync routes")
    write_routes: List[Tuple[str, set[str]]] = []
    for route in app.routes:
        methods = getattr(route, "methods", set())
        path = getattr(route, "path", "")
        if any(method in methods for method in {"POST", "PATCH", "DELETE"}) and ("apply" in path or "sync" in path):
            write_routes.append((path, methods))
    if write_routes:
        print(f"  ✗ FAILED: found apply/sync write routes: {write_routes}")
        return False
    print("  ✓ no apply/sync write routes")
    return True


def main() -> int:
    print("=" * 60)
    print("K3G Web UI Safety Tests — FASE 3.10")
    print("=" * 60)

    backups = _backup_response_artifacts()
    _clean_response_artifacts()

    tests = [
        test_imports,
        test_pending_items_get,
        test_get_valid_item,
        test_get_invalid_item,
        test_post_service_team_valid,
        test_post_network_ops_valid,
        test_post_bgp_valid,
        test_invalid_service_type,
        test_invalid_criticality,
        test_invalid_asn,
        test_object_key_traversal_blocked,
        test_secret_blocked,
        test_download_csv_allowed,
        test_download_csv_allowed_reports_prefix,
        test_download_sensitive_blocked,
        test_ip_detection_helpers,
        test_ip_validate_with_detected_mapping,
        test_ip_validate_service_relation_required,
        test_week1_validation_accepts_relation_type,
        test_csv_header,
        test_update_same_object_key,
        test_audit_created,
        test_modal_buttons_present,
        test_run_validation_endpoint,
        test_finalize_with_restrictions,
        test_finalize_when_complete,
        test_validation_dashboard,
        test_week2_review_pages,
        test_week2_decision_validation_script,
        test_week2_promotion_script_only_promotes_approved,
        test_week2_queue_has_proposed_approvals,
        test_uat_report_script,
        test_uat_archive_preserves_audit,
        test_uat_reset_requires_confirmation,
        test_uat_keep_as_real_requires_confirmation,
        test_no_netbox_write,
        test_no_applyplan,
        test_no_approvalrecord,
        test_no_apply_sync_routes,
    ]

    results: List[bool] = []
    try:
        for test in tests:
            try:
                results.append(test())
            except Exception as exc:
                print(f"  ✗ EXCEPTION: {exc}")
                results.append(False)
    finally:
        _restore_response_artifacts(backups)

    print("\n" + "=" * 60)
    passed = sum(1 for result in results if result)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
