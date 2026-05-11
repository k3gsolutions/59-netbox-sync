"""Tests for interface description pending-item response fields."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from webui.services.response_forms import build_pending_item_schema, validate_response_payload
from webui.services.validators import parse_interface_description


def test_parse_interface_description_accepts_unified_examples():
    examples = [
        "CLI|CID-10492|EMPRESA-ABC|Eth1/1|500M|INTERNET_MNS-DC01",
        "OP|OP-EMB-001|EMBRATEL|Ten0/1/2|10G|TRANSIT_MNS-DC01",
        "PTP|L2-30491|EMPRESA-XYZ|Gi0/0|1G|A:MNS-DC01_B:BVA-POP01",
        "PTMP|L2-30491|EMPRESA-XYZ|Gi0/0|1G|A:MNS-DC01_B:BVA-POP01",
        "EN|CIR-001|4WNET-MNS-KTG-RA|XG-0/0/1|100G|MANAUS_TO_PFG",
    ]
    for example in examples:
        valid, parsed, errors = parse_interface_description(example)
        assert valid, errors
        assert parsed["svc"] in {"CLI", "OP", "PTP", "PTMP", "EN"}


def test_interface_description_pending_schema_includes_proposed_description():
    item = {
        "object_type": "interface",
        "object_key": "GigabitEthernet0/0/0",
        "responsible_team": "Service Team",
        "responsible_team_slug": "service-team",
        "missing_fields": ["description"],
        "current_status": "pending",
    }
    schema = build_pending_item_schema(item)
    field_names = [field["name"] for field in schema["fields"]]
    description_field = next(field for field in schema["fields"] if field["name"] == "proposed_description")
    assert "proposed_description" in field_names
    assert "SVC|CID|HOST_REMOTO|PORTA_REMOTA|BANDA|COMENTARIO_OU_ROLE" in description_field["help"]


def test_interface_description_response_validates_pipe_format():
    item = {
        "object_type": "interface",
        "object_key": "GigabitEthernet0/0/0",
        "responsible_team": "Service Team",
        "missing_fields": ["description"],
    }
    payload = {
        "status": "answered",
        "updated_by": "netops",
        "proposed_description": "bad description",
        "evidence": "descricao revisada",
    }
    valid, errors, _ = validate_response_payload(item, payload)
    assert not valid
    assert any("proposed_description" in error for error in errors)

    payload["proposed_description"] = "EN|CIR-001|4WNET-MNS-KTG-RA|XG-0/0/1|100G|MANAUS_TO_PFG"
    valid, errors, _ = validate_response_payload(item, payload)
    assert valid, errors
