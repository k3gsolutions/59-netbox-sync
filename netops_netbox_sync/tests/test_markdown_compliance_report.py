from unittest.mock import patch

from app.reports.markdown_compliance import render_compliance_report
from app.schemas.analyze import (
    AnalyzeResult,
    AppliedInventorySummary,
    AnalyzeWarning,
)
from app.schemas.compliance import ComplianceDivergence, SummaryDiffItem, ComplianceSummary


def test_render_compliance_report_includes_hostname_and_applied_summary():
    result = AnalyzeResult(
        hostname="test-device",
        device_id=42,
        mode="read-only",
        netbox_loaded=True,
        compliance_enabled=True,
        applied_summary=AppliedInventorySummary(
            interfaces=1,
            ip_addresses=1,
            vrfs=1,
            vlans=1,
            bgp_sessions=1,
            route_policies=0,
            prefix_lists=0,
            as_path_filters=0,
            communities=0,
            community_lists=0,
        ),
        documented_summary=AppliedInventorySummary(
            interfaces=1,
            ip_addresses=1,
            vrfs=1,
            vlans=1,
            bgp_sessions=1,
            route_policies=0,
            prefix_lists=0,
            as_path_filters=0,
            communities=0,
            community_lists=0,
        ),
        summary_diff=[SummaryDiffItem(metric="interfaces", applied=1, documented=1, delta=0, status="match")],
        divergences=[],
        warnings=[AnalyzeWarning(code="TEST", severity="info", message="Teste")],
    )

    report = render_compliance_report(result)

    assert "# Relatório de Compliance — test-device" in report
    assert "| Interfaces | 1 |" in report
    assert "| IPs | 1 |" in report
    assert "NetBox não foi carregado" not in report


def test_render_compliance_report_separates_aggregated_from_object_divergences():
    """Aggregated divergences (no object_type) appear in section 5, object in section 6."""
    aggregated_div = ComplianceDivergence(
        code="MISSING_IN_NETBOX",
        severity="low",
        scope="interfaces",
        message="1 interface no dispositivo não está no NetBox.",
        evidence={"applied": 1, "documented": 0},
        recommendation="Investigar interfaces faltantes.",
        preferred_action="review",
        object_type=None,
        object_key=None,
    )
    object_div = ComplianceDivergence(
        code="INTERFACE_MISSING_IN_NETBOX",
        severity="medium",
        scope="interfaces",
        message="Interface eth0 existe no dispositivo, mas não no NetBox.",
        evidence={"applied": 1, "documented": 0},
        recommendation="Criar interface no NetBox.",
        preferred_action="fix_netbox",
        object_type="interface",
        object_key="eth0",
    )

    result = AnalyzeResult(
        hostname="test-device",
        device_id=42,
        mode="read-only",
        netbox_loaded=True,
        compliance_enabled=True,
        applied_summary=AppliedInventorySummary(),
        documented_summary=AppliedInventorySummary(),
        summary_diff=[],
        divergences=[aggregated_div, object_div],
        warnings=[],
    )

    report = render_compliance_report(result)

    # Both sections must exist
    assert "## 5. Divergências agregadas" in report
    assert "## 6. Divergências por objeto" in report

    # Aggregated divergence in report but not with object_type column
    assert "MISSING_IN_NETBOX" in report
    # Object divergence must be present
    assert "INTERFACE_MISSING_IN_NETBOX" in report
    assert "eth0" in report


def test_render_compliance_report_filters_aggregated_no_object_type():
    """Divergences with empty object_type appear only in aggregated section."""
    div_no_type = ComplianceDivergence(
        code="MISSING_IN_NETBOX",
        severity="low",
        scope="interfaces",
        message="Some interfaces missing.",
        evidence={},
        recommendation="Review.",
        preferred_action="review",
        object_type=None,
        object_key=None,
    )

    result = AnalyzeResult(
        hostname="test-device",
        device_id=42,
        mode="read-only",
        netbox_loaded=True,
        compliance_enabled=True,
        applied_summary=AppliedInventorySummary(),
        documented_summary=AppliedInventorySummary(),
        summary_diff=[],
        divergences=[div_no_type],
        warnings=[],
    )

    report = render_compliance_report(result)

    # Must have aggregated section
    assert "## 5. Divergências agregadas" in report
    # Should NOT have object divergences message "Nenhuma divergência por objeto"
    assert "Nenhuma divergência por objeto detectada." in report


def test_render_compliance_report_includes_divergences_and_actions():
    result = AnalyzeResult(
        hostname="test-device",
        device_id=42,
        mode="read-only",
        netbox_loaded=True,
        compliance_enabled=True,
        applied_summary=AppliedInventorySummary(),
        documented_summary=AppliedInventorySummary(),
        summary_diff=[],
        divergences=[
            ComplianceDivergence(
                code="INTERFACE_MISSING_IN_NETBOX",
                severity="medium",
                scope="interfaces",
                message="Interface eth0 existe no dispositivo, mas não no NetBox.",
                evidence={"applied": 1, "documented": 0},
                recommendation="Investigar.",
                preferred_action="fix_netbox",
                object_type="interface",
                object_key="eth0",
            )
        ],
        warnings=[AnalyzeWarning(code="WARN", severity="low", message="Aviso")],
    )

    report = render_compliance_report(result)

    assert "INTERFACE_MISSING_IN_NETBOX" in report
    assert "fix_netbox" in report
    assert "WARN" in report
    assert "Corrigir NetBox" in report


def test_render_compliance_report_handles_missing_documented_summary():
    result = AnalyzeResult(
        hostname="test-device",
        device_id=None,
        mode="read-only",
        netbox_loaded=False,
        compliance_enabled=False,
        applied_summary=AppliedInventorySummary(),
        documented_summary=None,
        summary_diff=[],
        divergences=[],
        warnings=[],
    )

    report = render_compliance_report(result)

    assert "NetBox não foi carregado" in report
    assert "Nenhuma divergência por objeto detectada." in report


def test_render_compliance_report_sections_in_order():
    """Verify sections are numbered correctly: 5=aggregated, 6=object, 7=warnings, 8=actions, 9=security."""
    result = AnalyzeResult(
        hostname="test-device",
        device_id=1,
        mode="read-only",
        netbox_loaded=True,
        compliance_enabled=True,
        applied_summary=AppliedInventorySummary(),
        documented_summary=AppliedInventorySummary(),
        summary_diff=[],
        divergences=[],
        warnings=[AnalyzeWarning(code="TEST", severity="info", message="Test warning")],
    )

    report = render_compliance_report(result)

    # Check sections exist in order
    assert "## 5. Divergências agregadas" in report
    assert "## 6. Divergências por objeto" in report
    assert "## 7. Warnings" in report
    assert "## 8. Ações recomendadas" in report
    assert "## 9. Observações de segurança" in report

    # Verify order by checking indices
    idx_5 = report.index("## 5. Divergências agregadas")
    idx_6 = report.index("## 6. Divergências por objeto")
    idx_7 = report.index("## 7. Warnings")
    idx_8 = report.index("## 8. Ações recomendadas")
    idx_9 = report.index("## 9. Observações de segurança")

    assert idx_5 < idx_6 < idx_7 < idx_8 < idx_9


def test_render_compliance_report_no_password_in_output():
    """Ensure no password/token leaks in report."""
    result = AnalyzeResult(
        hostname="test-device",
        device_id=42,
        mode="read-only",
        netbox_loaded=True,
        compliance_enabled=True,
        applied_summary=AppliedInventorySummary(),
        documented_summary=AppliedInventorySummary(),
        summary_diff=[],
        divergences=[],
        warnings=[],
    )

    report = render_compliance_report(result)

    assert "password" not in report.lower()
    assert "secret" not in report.lower()
    assert "token" not in report.lower()
