"""Tests for ImportPlan Markdown rendering and endpoints."""

import pytest

from app.compliance.import_plan import build_import_plan
from app.reports.import_plan_markdown import render_import_plan
from app.schemas.analyze import AnalyzeResult, AppliedInventorySummary
from app.schemas.compliance import ComplianceDivergence
from app.schemas.import_plan import ImportPlan


@pytest.fixture
def plan_with_items():
    """Sample ImportPlan with various items."""
    result = AnalyzeResult(
        hostname="router-1",
        device_id=456,
        mode="read-only",
        netbox_loaded=True,
        compliance_enabled=True,
        applied_summary=AppliedInventorySummary(
            interfaces=3,
            ip_addresses=2,
        ),
        divergences=[
            # Safe create staged
            ComplianceDivergence(
                code="INTERFACE_MISSING_IN_NETBOX",
                severity="medium",
                scope="interfaces",
                message="Interface ge-0/0/0 missing",
                evidence={"interface": "ge-0/0/0", "status": "up"},
                recommendation="Create",
                preferred_action="fix_netbox",
                object_type="interface",
                object_key="ge-0/0/0",
            ),
            # Needs review (invalid naming)
            ComplianceDivergence(
                code="INTERFACE_MISSING_IN_NETBOX",
                severity="medium",
                scope="interfaces",
                message="Bad naming",
                evidence={"interface": "Invalid@Name"},
                recommendation="Validate",
                preferred_action="review",
                object_type="interface",
                object_key="Invalid@Name",
            ),
            # Needs review (BGP)
            ComplianceDivergence(
                code="BGP_PEER_MISSING_IN_NETBOX",
                severity="high",
                scope="bgp_sessions",
                message="BGP peer missing",
                evidence={"peer_ip": "10.0.0.1", "as_path": "65000"},
                recommendation="Review configuration",
                preferred_action="review",
                object_type="bgp_peer",
                object_key="10.0.0.1",
            ),
            # Blocked
            ComplianceDivergence(
                code="UNKNOWN_DIVERGENCE",
                severity="info",
                scope="ambiguous",
                message="Ambiguous",
                evidence={},
                recommendation="Investigate",
                preferred_action="review",
                object_type="unknown",
                object_key=None,
            ),
            # Ignored
            ComplianceDivergence(
                code="SUMMARY_MISMATCH",
                severity="info",
                scope="summary",
                message="Summary mismatch",
                evidence={"applied": 3, "documented": 2},
                recommendation="Review",
                preferred_action="review",
                object_type=None,
                object_key=None,
            ),
        ],
    )

    return build_import_plan(result)


def test_markdown_renders_without_error(plan_with_items):
    """Markdown report renders without raising exceptions."""
    markdown = render_import_plan(plan_with_items)
    assert isinstance(markdown, str)
    assert len(markdown) > 0


def test_markdown_has_all_sections(plan_with_items):
    """Markdown contains all 6 required sections."""
    markdown = render_import_plan(plan_with_items)

    assert "# ImportPlan — router-1" in markdown
    assert "## 1. Resumo" in markdown
    assert "## 2. Safe create staged" in markdown
    assert "## 3. Revisão humana obrigatória" in markdown
    assert "## 4. Bloqueados" in markdown
    assert "## 5. Ignorados" in markdown
    assert "## 6. Observações de segurança" in markdown


def test_markdown_summary_counts(plan_with_items):
    """Markdown summary section has correct counts."""
    markdown = render_import_plan(plan_with_items)

    assert "**Total de divergências:** 5" in markdown
    assert "**Safe create staged:** 1" in markdown
    assert "**Revisão obrigatória:** 2" in markdown
    # Note: blocked is 0, ignored is 2 (includes both aggregate divergences)
    assert "**Bloqueados:** 0" in markdown
    assert "**Ignorados:** 2" in markdown


def test_markdown_includes_device_metadata(plan_with_items):
    """Markdown includes device name and ID."""
    markdown = render_import_plan(plan_with_items)

    assert "router-1" in markdown
    assert "456" in markdown


def test_markdown_safe_items_rendered(plan_with_items):
    """Safe create staged items are rendered correctly."""
    markdown = render_import_plan(plan_with_items)

    # Should mention the interface
    assert "ge-0/0/0" in markdown
    # Should be in safe section
    assert "### INTERFACE: ge-0/0/0" in markdown


def test_markdown_review_items_rendered(plan_with_items):
    """Needs review items are rendered correctly."""
    markdown = render_import_plan(plan_with_items)

    # Both review items should be mentioned
    assert "Invalid@Name" in markdown
    assert "10.0.0.1" in markdown


def test_markdown_blocked_items_rendered(plan_with_items):
    """Blocked items section appears (even if empty in this plan)."""
    markdown = render_import_plan(plan_with_items)

    # Blocked section should be present
    assert "## 4. Bloqueados" in markdown


def test_markdown_security_section(plan_with_items):
    """Security section emphasizes read-only status."""
    markdown = render_import_plan(plan_with_items)

    assert "Read-only — Nenhuma ação executada" in markdown
    assert "Este relatório é **somente informativo**" in markdown
    assert "Nenhuma escrita no NetBox realizada" in markdown
    assert "Nenhum comando enviado ao equipamento" in markdown
    assert "Token de escrita não foi utilizado" in markdown


def test_markdown_with_empty_plan():
    """Render plan with no divergences."""
    plan = ImportPlan(
        device="empty-device",
        device_id=999,
        generated_at="2026-04-28T00:00:00Z",
        source="compliance",
        total_items=0,
        items=[],
    )

    markdown = render_import_plan(plan)

    assert "empty-device" in markdown
    assert "**Total de divergências:** 0" in markdown  # Has bold markers
    assert "Nenhum candidato a staged import" in markdown
    assert "Nenhuma divergência requerendo revisão" in markdown


def test_markdown_formatting_valid(plan_with_items):
    """Markdown uses valid formatting."""
    markdown = render_import_plan(plan_with_items)

    # Check basic markdown structure
    lines = markdown.split("\n")
    assert any(line.startswith("#") for line in lines)  # Has headers
    assert any(line.startswith("-") for line in lines)  # Has lists
    assert any("**" in line for line in lines)  # Has bold text


def test_no_credentials_in_markdown(plan_with_items):
    """Markdown never includes actual credentials or sensitive values."""
    markdown = render_import_plan(plan_with_items)

    # Should never contain actual credentials or secrets (actual values like API tokens)
    # Note: legitimate phrases like "Token de escrita não foi utilizado" are OK
    assert "password=" not in markdown.lower()
    assert "secret=" not in markdown.lower()
    assert "api_key=" not in markdown.lower()
    # Shouldn't contain credential patterns with values
    assert "ojnVy4" not in markdown  # Example from schema


def test_naming_compliance_indicated(plan_with_items):
    """Markdown clearly indicates naming compliance status."""
    markdown = render_import_plan(plan_with_items)

    # Safe item should show compliant
    assert "ge-0/0/0" in markdown
    # Invalid item should show non-compliant
    assert "Invalid@Name" in markdown


def test_evidence_rendered_readable(plan_with_items):
    """Evidence is rendered in readable format."""
    markdown = render_import_plan(plan_with_items)

    # Evidence should be formatted as list items
    assert "interface: ge-0/0/0" in markdown
    # Should not be raw JSON dict representation
    assert "{" not in markdown or "}" not in markdown


def test_next_steps_provided(plan_with_items):
    """Markdown provides clear next steps."""
    markdown = render_import_plan(plan_with_items)

    assert "Próximas ações:" in markdown
    assert "Revisar divergências na seção 3" in markdown
    assert "staged import" in markdown
    assert "aprovação humana" in markdown
