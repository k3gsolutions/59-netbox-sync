(function () {
  const BLOCKED_TERMS = [
    "token",
    "password",
    "secret",
    "netbox_write_token",
    "private key",
    "bearer",
    "authorization",
  ];

  const state = {
    device: null,
    item: null,
    schema: null,
    safeItemId: null,
  };

  function $(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function showModal() {
    const backdrop = $("pending-item-modal-backdrop");
    const modal = $("pending-item-modal");
    if (backdrop) backdrop.classList.add("open");
    if (modal) modal.classList.add("open");
  }

  function hideModal() {
    const backdrop = $("pending-item-modal-backdrop");
    const modal = $("pending-item-modal");
    if (backdrop) backdrop.classList.remove("open");
    if (modal) modal.classList.remove("open");
  }

  function clearErrors() {
    document.querySelectorAll("[data-field-error]").forEach((el) => {
      el.textContent = "";
      el.classList.add("hidden");
    });
  }

  function setFieldError(fieldName, message) {
    const el = document.querySelector(`[data-field-error="${fieldName}"]`);
    if (!el) return;
    el.textContent = message;
    el.classList.remove("hidden");
  }

  function setModalMessage(message, kind) {
    const el = $("pending-item-modal-message");
    if (!el) return;
    el.textContent = message;
    el.className = `alert alert-${kind || "info"}`;
    el.classList.remove("hidden");
  }

  function hideModalMessage() {
    const el = $("pending-item-modal-message");
    if (!el) return;
    el.textContent = "";
    el.className = "alert alert-info hidden";
  }

  function statusBadgeClass(status) {
    if (status === "answered") return "badge badge-success";
    if (status === "needs_clarification") return "badge badge-warning";
    if (status === "blocked" || status === "rejected") return "badge badge-danger";
    return "badge badge-pending";
  }

  function renderField(field) {
    const value = field.value ?? "";
    const requiredMark = field.required ? " *" : "";
    const helpText = field.help || (field.required ? "Obrigatório" : "");
    let inputHtml = "";
    const baseAttrs = `name="${escapeHtml(field.name)}" id="pending-field-${escapeHtml(field.name)}"`;

    const requiredAttr = field.required ? " required" : "";
    const readonlyAttr = field.readonly ? " readonly" : "";

    if (field.type === "select") {
      const options = (field.choices || [])
        .map((choice) => {
          const selected = String(choice) === String(value) ? " selected" : "";
          return `<option value="${escapeHtml(choice)}"${selected}>${escapeHtml(choice)}</option>`;
        })
        .join("");
      inputHtml = `<select ${baseAttrs}${requiredAttr}${readonlyAttr}>${field.required ? '<option value="">Selecione...</option>' : '<option value="">Opcional</option>'}${options}</select>`;
    } else if (field.type === "textarea") {
      inputHtml = `<textarea ${baseAttrs}${requiredAttr}${readonlyAttr} rows="4">${escapeHtml(value)}</textarea>`;
    } else {
      const inputType = field.type === "number" ? "number" : "text";
      const extra = field.type === "number" ? ' min="1" max="4294967295" inputmode="numeric"' : "";
      inputHtml = `<input type="${inputType}" ${baseAttrs}${requiredAttr}${readonlyAttr} value="${escapeHtml(value)}"${extra}>`;
    }

    return `
      <div class="form-group">
        <label for="pending-field-${escapeHtml(field.name)}">${escapeHtml(field.label)}${requiredMark}</label>
        ${inputHtml}
        <div class="form-error hidden" data-field-error="${escapeHtml(field.name)}"></div>
        ${helpText ? `<div class="input-help">${escapeHtml(helpText)}</div>` : ""}
      </div>
    `;
  }

  function renderForm(schema, item) {
    const container = $("pending-item-form-fields");
    if (!container) return;
    container.innerHTML = schema.fields.map(renderField).join("");
    const safeId = $("pending-item-safe-id");
    if (safeId) safeId.value = item.safe_item_id;
    const device = $("pending-item-device");
    if (device) device.value = state.device || "";
    const title = $("pending-item-modal-title");
    if (title) title.textContent = `Editar pendência — ${item.object_key}`;
    const context = $("pending-item-modal-context");
    if (context) {
      const ipBadges = [];
      if (item.object_type === "ip_address") {
        if (item.detected_interface) ipBadges.push('<span class="badge badge-info">Interface detectada</span>');
        else ipBadges.push('<span class="badge badge-warning">Mapeamento ausente</span>');
        if (item.detected_vrf) ipBadges.push('<span class="badge badge-info">VRF detectada</span>');
        if (item.status_hint) ipBadges.push(`<span class="badge badge-neutral">${escapeHtml(item.status_hint)}</span>`);
      }
      context.innerHTML = `
        <div class="pending-modal-context-grid">
          <div><span class="pending-modal-label">device</span><div class="mono">${escapeHtml(item.device)}</div></div>
          <div><span class="pending-modal-label">object_type</span><div class="mono">${escapeHtml(item.object_type)}</div></div>
          <div><span class="pending-modal-label">responsible_team</span><div class="mono">${escapeHtml(item.responsible_team)}</div></div>
          <div><span class="pending-modal-label">missing_fields</span><div class="mono">${escapeHtml((item.missing_fields || []).join(", ") || "nenhum")}</div></div>
        </div>
        ${item.object_type === "ip_address" ? `
          <div class="alert alert-info">
            Se a interface/VRF já foi detectada pelo coletor, confirme os valores abaixo. Edite apenas se estiver incorreto. Se o IP não pertence a um serviço específico, marque relation_type como infrastructure, backbone, loopback ou management.
          </div>
          <div class="pending-ip-badges">${ipBadges.join("")}</div>
        ` : ""}
      `;
    }
  }

  function checkBlockedTerms(value) {
    const lower = String(value || "").toLowerCase();
    return BLOCKED_TERMS.some((term) => lower.includes(term));
  }

  function validatePendingItemForm() {
    clearErrors();
    hideModalMessage();

    const form = $("pending-item-form");
    if (!form || !state.item || !state.schema) return false;

    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());
    const status = String(payload.status || "").trim();
    let ok = true;

    if (!payload.updated_by || !String(payload.updated_by).trim()) {
      setFieldError("updated_by", "updated_by obrigatório");
      ok = false;
    }

    if (!status) {
      setFieldError("status", "Status obrigatório");
      ok = false;
    }

    const requiredOnAnswered = {
      "subinterface": ["tenant", "service_type", "criticality", "owner", "evidence"],
      "bgp_peer": ["remote_asn", "remote_bgp_group", "policy_intent", "owner", "criticality", "evidence"],
    };

    const itemType = String(state.item.object_type || "").toLowerCase();
    const requiredFields = status === "answered" ? (requiredOnAnswered[itemType] || []) : [];
    requiredFields.forEach((fieldName) => {
      if (!String(payload[fieldName] || "").trim()) {
        setFieldError(fieldName, `${fieldName} obrigatório`);
        ok = false;
      }
    });

    if (itemType === "ip_address" && status === "answered") {
      if (!String(payload.relation_type || "").trim()) {
        setFieldError("relation_type", "relation_type obrigatório");
        ok = false;
      }
      if (!String(payload.interface || "").trim() && !String(state.item.detected_interface || "").trim()) {
        setFieldError("interface", "Interface obrigatória");
        ok = false;
      }
      if (!String(payload.vrf || "").trim() && !String(state.item.detected_vrf || "").trim()) {
        setFieldError("vrf", "VRF obrigatória");
        ok = false;
      }
      if (String(payload.relation_type || "") === "service" && !String(payload.service_relation || "").trim()) {
        setFieldError("service_relation", "Relação de serviço obrigatória");
        ok = false;
      }
      if (String(payload.relation_type || "") === "unknown" && !String(payload.notes || "").trim()) {
        setFieldError("notes", "Observações obrigatórias");
        ok = false;
      }
    }

    if (["blocked", "rejected", "needs_clarification"].includes(status) && !String(payload.notes || "").trim()) {
      setFieldError("notes", "Observações obrigatórias");
      ok = false;
    }

    Object.entries(payload).forEach(([field, value]) => {
      if (String(value || "").trim() && checkBlockedTerms(value)) {
        setFieldError(field, `${field} contém palavra bloqueada`);
        ok = false;
      }
    });

    if (itemType === "bgp_peer" && payload.remote_asn) {
      const asn = Number(payload.remote_asn);
      if (!Number.isInteger(asn) || asn < 1 || asn > 4294967295) {
        setFieldError("remote_asn", "remote_asn deve estar entre 1 e 4294967295");
        ok = false;
      }
    }

    if (itemType === "ip_address" && payload.interface) {
      const patterns = [
        /^Eth-Trunk\d+(\.\d+)?$/,
        /^GigabitEthernet\d+\/\d+\/\d+(\.\d+)?$/,
        /^10GE\d+\/\d+\/\d+$/,
        /^LoopBack\d+$/,
        /^Vlanif\d+$/,
      ];
      if (!patterns.some((pattern) => pattern.test(String(payload.interface)))) {
        setFieldError("interface", "Formato de interface inválido");
        ok = false;
      }
    }

    if (itemType === "ip_address" && payload.vrf) {
      const okVrf = /^(_public_|default|[a-zA-Z0-9_-]+)$/.test(String(payload.vrf));
      if (!okVrf) {
        setFieldError("vrf", "Formato de VRF inválido");
        ok = false;
      }
    }

    return ok;
  }

  function updateRowAfterSave(item, payload) {
    const row = $(`pending-row-${item.safe_item_id}`);
    if (!row) return;

    const badge = $(`pending-status-${item.safe_item_id}`);
    if (badge) {
      badge.className = statusBadgeClass(payload.status);
      badge.textContent = payload.status;
    }

    const missing = $(`missing-fields-${item.safe_item_id}`);
    if (missing) {
      missing.textContent = payload.status === "answered" ? "nenhum" : (item.missing_fields || []).join(", ") || "nenhum";
      missing.classList.toggle("text-muted", payload.status !== "answered");
    }

    const button = $(`pending-button-${item.safe_item_id}`);
    if (button) {
      button.textContent = payload.status === "answered" ? "Editar pendência" : "Completar pendência";
    }
  }

  function updateValidationSummary(summary) {
    const targets = {
      validated: $("validation-count-validated"),
      ready_for_review: $("validation-count-ready_for_review"),
      still_pending: $("validation-count-still_pending"),
      needs_clarification: $("validation-count-needs_clarification"),
      blocked: $("validation-count-blocked"),
      rejected: $("validation-count-rejected"),
    };
    Object.entries(targets).forEach(([key, el]) => {
      if (el && summary && Object.prototype.hasOwnProperty.call(summary, key)) {
        el.textContent = String(summary[key]);
      }
    });
  }

  async function openPendingItemModal(itemId, device) {
    state.device = device || state.device || document.body.dataset.device || "";
    if (!state.device) return;

    const url = `/service-engagement/${encodeURIComponent(state.device)}/pending-items/${encodeURIComponent(itemId)}`;
    hideModalMessage();
    clearErrors();

    const response = await fetch(url, {
      headers: { Accept: "application/json" },
    });
    const data = await response.json();
    if (!response.ok || !data.success) {
      setModalMessage(data.error || "Não foi possível carregar a pendência.", "danger");
      showModal();
      return;
    }

    state.item = data.item;
    state.schema = data.schema;
    state.safeItemId = itemId;
    renderForm(data.schema, data.item);
    showModal();
  }

  function closePendingItemModal() {
    hideModal();
    hideModalMessage();
    clearErrors();
  }

  async function runValidationNow(device) {
    const url = `/service-engagement/${encodeURIComponent(device)}/responses/run-validation`;
    const response = await fetch(url, {
      method: "POST",
      headers: { Accept: "application/json" },
    });
    return response.json();
  }

  async function finalizeResponses(device) {
    const url = `/service-engagement/${encodeURIComponent(device)}/responses/finalize`;
    const response = await fetch(url, {
      method: "POST",
      headers: { Accept: "application/json" },
    });
    return response.json();
  }

  function renderConventionViolations(violations) {
    if (!violations || violations.length === 0) return "";

    const severityMap = {
      blocker: { icon: "🔒", color: "red", label: "BLOQUEADOR" },
      error: { icon: "❌", color: "orange", label: "ERRO" },
      warning: { icon: "⚠️", color: "yellow", label: "ALERTA" },
      info: { icon: "ℹ️", color: "blue", label: "INFO" },
    };

    const violationHtml = violations
      .map((v) => {
        const severity = v.severity || "info";
        const meta = severityMap[severity] || severityMap.info;
        const ruleId = escapeHtml(v.rule_id || "UNKNOWN");
        const message = escapeHtml(v.message_pt || v.message || "Violação de conformidade detectada");
        return `
          <div class="convention-violation" style="border-left: 4px solid ${meta.color}; padding: 8px 12px; margin: 8px 0; background-color: #f5f5f5;">
            <div style="display: flex; gap: 8px; align-items: start;">
              <span style="font-size: 18px;">${meta.icon}</span>
              <div style="flex: 1;">
                <div style="font-weight: bold; font-size: 12px; color: #666;">
                  ${meta.label} — ${ruleId}
                </div>
                <div style="margin-top: 4px; font-size: 13px; color: #333;">
                  ${message}
                </div>
              </div>
            </div>
          </div>
        `;
      })
      .join("");

    return `
      <div class="convention-violations-section">
        <div style="font-weight: bold; margin-bottom: 8px; font-size: 12px; text-transform: uppercase; color: #666;">
          Resultado da Validação de Conformidade
        </div>
        ${violationHtml}
      </div>
    `;
  }

  async function submitPendingItemResponse(closeAfterSave, validateAfterSave) {
    if (!validatePendingItemForm()) {
      setModalMessage("Corrija os campos destacados antes de salvar.", "warning");
      return false;
    }

    const form = $("pending-item-form");
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());
    const url = `/service-engagement/${encodeURIComponent(state.device)}/pending-items/${encodeURIComponent(state.safeItemId)}/response`;

    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    const violations = data.convention_violations || [];

    if (!response.ok || !data.success) {
      const errors = data.errors || [data.error || "Falha ao salvar a resposta."];
      const violationsHtml = renderConventionViolations(violations);
      const messageHtml = `
        <div>${errors.map((e) => `<div>${escapeHtml(e)}</div>`).join("")}</div>
        ${violationsHtml}
      `;
      const helper = $("pending-item-modal-message");
      if (helper) {
        helper.innerHTML = messageHtml;
        helper.className = "alert alert-danger";
        helper.classList.remove("hidden");
      }
      return false;
    }

    const pipeline = data.pipeline || {};
    updateRowAfterSave(state.item, payload);
    if (pipeline.validation) {
      updateValidationSummary(pipeline.validation);
    }

    const csvLink = `<a href="/reports/download?path=${escapeHtml(data.csv_path)}">Ver CSV gerado</a>`;
    const validationLink = `<a href="/service-engagement/${encodeURIComponent(state.device)}/validation">Ver validação</a>`;
    const finalizeLink = pipeline.week2_prepared ? `<a href="/service-engagement/${encodeURIComponent(state.device)}/week2-review">Abrir revisão da Semana 2</a>` : "";
    const violationsHtml = renderConventionViolations(violations);
    const helper = $("pending-item-modal-message");
    if (helper) {
      const nextAction = escapeHtml(pipeline.next_action || "Validação local executada.");
      const remaining = pipeline.validation ? Number(pipeline.validation.still_pending || 0) : 0;
      helper.innerHTML = `
        <div>${escapeHtml(data.message)}</div>
        <div class="mono">${escapeHtml(data.csv_path)}</div>
        <div>${nextAction}</div>
        <div>${remaining > 0 ? `Ainda existem ${remaining} pendências.` : "Todas as pendências foram respondidas."}</div>
        ${violationsHtml}
        <div class="pending-modal-links">${csvLink} ${validationLink} ${finalizeLink}</div>
      `;
      helper.className = "alert alert-success";
    }

    if (closeAfterSave) {
      closePendingItemModal();
      window.location.reload();
    }

    if (validateAfterSave) {
      const validation = await runValidationNow(state.device);
      if (validation && validation.validation) {
        updateValidationSummary(validation.validation);
      }
    }

    return true;
  }

  async function finalizeResponsesAndRefresh(device) {
    const result = await finalizeResponses(device || state.device || document.body.dataset.device || "");
    if (!result || !result.success) {
      setModalMessage(result.error || "Falha ao finalizar respostas.", "danger");
      return false;
    }
    if (result.validation) {
      updateValidationSummary(result.validation);
    }
    setModalMessage(result.next_action || "Validação local executada.", "success");
    window.location.reload();
    return true;
  }

  function togglePendingItemDetail(id) {
    const el = $(id);
    if (!el) return;
    el.classList.toggle("hidden");
  }

  window.openPendingItemModal = openPendingItemModal;
  window.closePendingItemModal = closePendingItemModal;
  window.validatePendingItemForm = validatePendingItemForm;
  window.submitPendingItemResponse = submitPendingItemResponse;
  window.runValidationNow = runValidationNow;
  window.finalizeResponsesAndRefresh = finalizeResponsesAndRefresh;
  window.togglePendingItemDetail = togglePendingItemDetail;
})();
