import os
from unittest.mock import patch

from fastapi.testclient import TestClient
from netmiko.exceptions import NetMikoAuthenticationException

from app.api.main import app
from app.schemas.analyze import AnalyzeResult, AppliedInventorySummary

AUTH_HEADERS = {"X-API-Key": os.environ["API_KEY"]} if os.environ.get("API_KEY") else {}
client = TestClient(app)


def test_openapi_includes_compliance_analyze_and_preserves_routes():
    data = app.openapi()
    assert "/compliance/analyze" in data["paths"]
    assert "/compliance/analyze/report" in data["paths"]
    assert "/device/collect" in data["paths"]
    assert "/sync" in data["paths"]


@patch("app.api.routes.compliance._do_analyze")
def test_compliance_analyze_returns_read_only(mock_do_analyze):
    mock_do_analyze.return_value = AnalyzeResult(
        hostname="test-device",
        device_id=None,
        mode="read-only",
        netbox_loaded=False,
        compliance_enabled=False,
        applied_summary=AppliedInventorySummary(
            interfaces=1,
            ip_addresses=1,
            vrfs=0,
            vlans=0,
            bgp_sessions=0,
            route_policies=0,
            prefix_lists=0,
            as_path_filters=0,
            communities=0,
            community_lists=0,
        ),
        warnings=[
            {
                "code": "NETBOX_NOT_LOADED",
                "severity": "medium",
                "message": "NetBox inventory ainda não foi carregado nesta fase.",
            }
        ],
        next_steps=[
            "Implementar NetBoxInventory read-only.",
            "Comparar DeviceInventory vs NetBoxInventory.",
            "Gerar relatório de compliance.",
        ],
    )

    response = client.post(
        "/compliance/analyze",
        headers=AUTH_HEADERS,
        json={
            "device": {
                "host": "192.0.2.1",
                "username": "admin",
                "password": "secret",
                "port": 22,
            }
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "read-only"
    assert data["netbox_loaded"] is False
    assert data["compliance_enabled"] is False
    assert "password" not in data
    assert data["applied_summary"]["communities"] == 0
    assert data["applied_summary"]["community_lists"] == 0


@patch("app.api.routes.compliance._do_analyze")
def test_compliance_analyze_ssh_error_returns_502(mock_do_analyze):
    mock_do_analyze.side_effect = NetMikoAuthenticationException("authentication failed")
    response = client.post(
        "/compliance/analyze",
        headers=AUTH_HEADERS,
        json={
            "device": {
                "host": "192.0.2.1",
                "username": "admin",
                "password": "secret",
                "port": 22,
            }
        },
    )
    assert response.status_code == 502
    assert "SSH" in response.json()["detail"]


@patch("app.workflow.sync_device.sync_to_netbox")
@patch("app.workflow.sync_device.sync_bgp_plugin")
@patch("app.api.routes.compliance._do_analyze")
def test_compliance_analyze_report_returns_markdown(
    mock_do_analyze, mock_sync_bgp_plugin, mock_sync_to_netbox
):
    mock_do_analyze.return_value = AnalyzeResult(
        hostname="test-device",
        device_id=42,
        mode="read-only",
        netbox_loaded=True,
        compliance_enabled=True,
        applied_summary=AppliedInventorySummary(
            interfaces=1,
            ip_addresses=1,
            vrfs=0,
            vlans=0,
            bgp_sessions=0,
            route_policies=0,
            prefix_lists=0,
            as_path_filters=0,
            communities=0,
            community_lists=0,
        ),
        documented_summary=AppliedInventorySummary(
            interfaces=1,
            ip_addresses=1,
            vrfs=0,
            vlans=0,
            bgp_sessions=0,
            route_policies=0,
            prefix_lists=0,
            as_path_filters=0,
            communities=0,
            community_lists=0,
        ),
        summary_diff=[],
        divergences=[],
        warnings=[],
    )
    response = client.post(
        "/compliance/analyze/report",
        headers=AUTH_HEADERS,
        json={
            "device": {
                "host": "192.0.2.1",
                "username": "admin",
                "password": "secret",
                "port": 22,
            },
            "device_id": 42,
            "netbox": {
                "url": "http://netbox.local",
                "token": "token",
                "verify_ssl": False,
            },
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "# Relatório de Compliance" in response.text
    assert mock_sync_to_netbox.call_count == 0
    assert mock_sync_bgp_plugin.call_count == 0
