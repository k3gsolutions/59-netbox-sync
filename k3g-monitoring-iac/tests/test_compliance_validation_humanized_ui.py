"""Tests for humanized compliance validation UI."""

import pytest


def test_human_labels_visible_in_template():
    """Template contains human-readable decision labels."""
    # Key labels to find:
    # - "Precisa corrigir"
    # - "Precisa investigar melhor"
    # - "É falso positivo"
    # - "Aceito / Correto"
    # - "Bloquear avanço"
    # - "Ignorar por enquanto"

    # Read template file
    with open("/Users/keslleykssantos/projects/ativos/59-netbox_sync/k3g-monitoring-iac/webui/templates/compliance_job_detail.html") as f:
        content = f.read()

    assert "Precisa corrigir" in content
    assert "Precisa investigar melhor" in content
    assert "É falso positivo" in content
    assert "Aceito / Correto" in content
    assert "Bloquear avanço" in content


def test_severity_labels_humanized_in_template():
    """Template contains humanized severity labels, not raw 'error', 'warning'."""
    with open("/Users/keslleykssantos/projects/ativos/59-netbox_sync/k3g-monitoring-iac/webui/templates/compliance_job_detail.html") as f:
        content = f.read()

    # Should show "Crítico" instead of raw "error" in severity display
    assert "Crítico" in content
    assert "Atenção" in content
    assert "Bloqueador" in content


def test_technical_details_collapsible_in_template():
    """Template contains <details> tag for technical details."""
    with open("/Users/keslleykssantos/projects/ativos/59-netbox_sync/k3g-monitoring-iac/webui/templates/compliance_job_detail.html") as f:
        content = f.read()

    # Check for details element with class or just details tag
    assert "<details" in content
    assert "Detalhes" in content


def test_no_netbox_write_buttons_in_template():
    """Template does NOT contain 'Aplicar', 'Sync', 'ApplyPlan', 'ApprovalRecord' buttons in validation section."""
    with open("/Users/keslleykssantos/projects/ativos/59-netbox_sync/k3g-monitoring-iac/webui/templates/compliance_job_detail.html") as f:
        content = f.read()

    # These patterns should NOT appear in the validation section
    validation_section = content[content.find("Validação das Pendências"):content.find("</div>")]

    # No write operations in validation section
    assert "ApplyPlan" not in validation_section
    assert "ApprovalRecord" not in validation_section
    assert "/sync" not in validation_section.lower()


def test_safety_notice_present_in_template():
    """Template contains security notice about not altering NetBox."""
    with open("/Users/keslleykssantos/projects/ativos/59-netbox_sync/k3g-monitoring-iac/webui/templates/compliance_job_detail.html") as f:
        content = f.read()

    assert "não altera o NetBox" in content
    assert "não acessa o equipamento" in content


def test_progress_bar_in_template():
    """Template contains progress bar HTML."""
    with open("/Users/keslleykssantos/projects/ativos/59-netbox_sync/k3g-monitoring-iac/webui/templates/compliance_job_detail.html") as f:
        content = f.read()

    assert "progress-fill" in content
    assert "progress-label" in content


def test_filter_buttons_in_template():
    """Template contains filter button elements."""
    with open("/Users/keslleykssantos/projects/ativos/59-netbox_sync/k3g-monitoring-iac/webui/templates/compliance_job_detail.html") as f:
        content = f.read()

    assert 'data-filter="all"' in content
    assert 'data-filter="critical"' in content
    assert 'data-filter="bgp"' in content
    assert "filter-btn" in content


def test_preset_buttons_in_template():
    """Template contains preset button elements."""
    with open("/Users/keslleykssantos/projects/ativos/59-netbox_sync/k3g-monitoring-iac/webui/templates/compliance_job_detail.html") as f:
        content = f.read()

    assert "preset-btn" in content
    assert 'data-preset="bgp_state_down"' in content
    assert 'data-preset="bgp_no_description"' in content
    assert 'data-preset="parser_noise"' in content


def test_batch_save_button_in_template():
    """Template contains batch save button."""
    with open("/Users/keslleykssantos/projects/ativos/59-netbox_sync/k3g-monitoring-iac/webui/templates/compliance_job_detail.html") as f:
        content = f.read()

    assert 'id="save-all-btn"' in content
    assert "Salvar todas as validações" in content


def test_reviewer_input_field_in_template():
    """Template contains reviewer input field."""
    with open("/Users/keslleykssantos/projects/ativos/59-netbox_sync/k3g-monitoring-iac/webui/templates/compliance_job_detail.html") as f:
        content = f.read()

    assert 'id="reviewer-name"' in content
    assert "Seu nome" in content


def test_decision_select_dropdown_in_template():
    """Template contains decision select dropdown with humanized labels."""
    with open("/Users/keslleykssantos/projects/ativos/59-netbox_sync/k3g-monitoring-iac/webui/templates/compliance_job_detail.html") as f:
        content = f.read()

    # Should have decision-select elements
    assert "decision-select" in content
    # Should have the humanized labels as options
    assert "Precisa corrigir" in content
    assert "Precisa investigar melhor" in content
    assert "É falso positivo" in content


def test_reason_textarea_in_template():
    """Template contains reason input textarea."""
    with open("/Users/keslleykssantos/projects/ativos/59-netbox_sync/k3g-monitoring-iac/webui/templates/compliance_job_detail.html") as f:
        content = f.read()

    assert "class=\"reason-input\"" in content
    assert 'placeholder="Observação..."' in content
