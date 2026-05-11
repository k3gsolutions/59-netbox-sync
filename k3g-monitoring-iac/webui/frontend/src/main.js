import './style.css'

// ── Nav active state ─────────────────────────────────────
function setActiveNav() {
  const path = window.location.pathname
  document.querySelectorAll('.nav-link').forEach(link => {
    const href = link.getAttribute('href')
    const isActive = href === '/'
      ? path === '/'
      : path.startsWith(href) && href !== '/'
    link.classList.toggle('active', isActive)
  })
}

// ── Header search ─────────────────────────────────────────
function initSearch() {
  const input = document.getElementById('global-search')
  if (!input) return
  let timer
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      const q = input.value.trim()
      if (q) window.location.href = `/search?q=${encodeURIComponent(q)}`
    }
  })
  // Keyboard shortcut: /
  document.addEventListener('keydown', e => {
    if (e.key === '/' && document.activeElement !== input) {
      e.preventDefault()
      input.focus()
      input.select()
    }
  })
}

// ── Toast notifications ───────────────────────────────────
function showToast(message, kind = 'info', duration = 4000) {
  let container = document.getElementById('toast-container')
  if (!container) {
    container = document.createElement('div')
    container.id = 'toast-container'
    container.style.cssText = `
      position:fixed; bottom:20px; right:20px; z-index:9999;
      display:flex; flex-direction:column; gap:8px;
    `
    document.body.appendChild(container)
  }

  const colors = {
    info: '#38bdf8', success: '#22d47a', warning: '#f5a623', danger: '#f0434b'
  }

  const toast = document.createElement('div')
  toast.style.cssText = `
    background:#1e2238; border:1px solid ${colors[kind] || colors.info};
    color:${colors[kind] || colors.info}; padding:12px 16px;
    border-radius:8px; font-size:13px; font-family:var(--sans);
    max-width:320px; box-shadow:0 4px 24px rgba(0,0,0,.5);
    animation:slideUp .2s ease; cursor:pointer;
  `
  toast.textContent = message
  toast.onclick = () => toast.remove()
  container.appendChild(toast)
  setTimeout(() => toast.remove(), duration)
}

// ── Modal helpers ─────────────────────────────────────────
const BLOCKED_TERMS = ['token','password','secret','netbox_write_token','private key','bearer','authorization']

const state = { device: null, item: null, schema: null, safeItemId: null }

function $(id) { return document.getElementById(id) }

function escapeHtml(v) {
  return String(v ?? '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;')
}

function showModal() {
  const bd = $('pending-item-modal-backdrop')
  const modal = $('pending-item-modal')
  if (bd) bd.classList.add('open')
  if (modal) modal.classList.add('open')
}

function hideModal() {
  const bd = $('pending-item-modal-backdrop')
  const modal = $('pending-item-modal')
  if (bd) bd.classList.remove('open')
  if (modal) modal.classList.remove('open')
}

function clearErrors() {
  document.querySelectorAll('[data-field-error]').forEach(el => {
    el.textContent = ''; el.classList.add('hidden')
  })
}

function setFieldError(name, msg) {
  const el = document.querySelector(`[data-field-error="${name}"]`)
  if (!el) return
  el.textContent = msg; el.classList.remove('hidden')
}

function setModalMessage(msg, kind) {
  const el = $('pending-item-modal-message')
  if (!el) return
  el.textContent = msg
  el.className = `alert alert-${kind || 'info'}`
  el.classList.remove('hidden')
}

function hideModalMessage() {
  const el = $('pending-item-modal-message')
  if (!el) return
  el.textContent = ''; el.className = 'alert alert-info hidden'
}

function statusBadgeClass(s) {
  if (s === 'answered') return 'badge badge-success'
  if (s === 'needs_clarification') return 'badge badge-warning'
  if (s === 'blocked' || s === 'rejected') return 'badge badge-danger'
  return 'badge badge-pending'
}

function renderField(field) {
  const val = field.value ?? ''
  const req = field.required ? ' *' : ''
  const help = field.help || (field.required ? 'Obrigatório' : '')
  const baseAttrs = `name="${escapeHtml(field.name)}" id="pending-field-${escapeHtml(field.name)}"`
  const reqAttr = field.required ? ' required' : ''
  const roAttr = field.readonly ? ' readonly' : ''
  let input = ''

  if (field.type === 'select') {
    const opts = (field.choices || []).map(c => {
      const sel = String(c) === String(val) ? ' selected' : ''
      return `<option value="${escapeHtml(c)}"${sel}>${escapeHtml(c)}</option>`
    }).join('')
    input = `<select ${baseAttrs}${reqAttr}${roAttr}><option value="">${field.required ? 'Selecione...' : 'Opcional'}</option>${opts}</select>`
  } else if (field.type === 'textarea') {
    input = `<textarea ${baseAttrs}${reqAttr}${roAttr} rows="4">${escapeHtml(val)}</textarea>`
  } else {
    const t = field.type === 'number' ? 'number' : 'text'
    const extra = field.type === 'number' ? ' min="1" max="4294967295" inputmode="numeric"' : ''
    input = `<input type="${t}" ${baseAttrs}${reqAttr}${roAttr} value="${escapeHtml(val)}"${extra}>`
  }

  return `
    <div class="form-group">
      <label for="pending-field-${escapeHtml(field.name)}">${escapeHtml(field.label)}${req}</label>
      ${input}
      <div class="form-error hidden" data-field-error="${escapeHtml(field.name)}"></div>
      ${help ? `<div class="form-help">${escapeHtml(help)}</div>` : ''}
    </div>
  `
}

function renderForm(schema, item) {
  const c = $('pending-item-form-fields')
  if (!c) return
  c.innerHTML = schema.fields.map(renderField).join('')
  const si = $('pending-item-safe-id'); if (si) si.value = item.safe_item_id
  const dv = $('pending-item-device'); if (dv) dv.value = state.device || ''
  const ti = $('pending-item-modal-title'); if (ti) ti.textContent = `Editar pendência — ${item.object_key}`
  const ctx = $('pending-item-modal-context')
  if (ctx) {
    const badges = []
    if (item.object_type === 'ip_address') {
      if (item.detected_interface) badges.push('<span class="badge badge-info">Interface detectada</span>')
      else badges.push('<span class="badge badge-warning">Mapeamento ausente</span>')
      if (item.detected_vrf) badges.push('<span class="badge badge-info">VRF detectada</span>')
      if (item.status_hint) badges.push(`<span class="badge badge-neutral">${escapeHtml(item.status_hint)}</span>`)
    }
    ctx.innerHTML = `
      <div class="pending-modal-context-grid">
        <div><span class="pending-modal-label">Dispositivo</span><div class="mono">${escapeHtml(item.device)}</div></div>
        <div><span class="pending-modal-label">Tipo de objeto</span><div class="mono">${escapeHtml(item.object_type)}</div></div>
        <div><span class="pending-modal-label">Time responsável</span><div class="mono">${escapeHtml(item.responsible_team)}</div></div>
        <div><span class="pending-modal-label">Campos ausentes</span><div class="mono">${escapeHtml((item.missing_fields||[]).join(', ')||'nenhum')}</div></div>
      </div>
      ${item.object_type === 'ip_address' ? `
        <div class="alert alert-info mt-8">
          <div class="alert-body">Se a interface/VRF já foi detectada, confirme os valores. Edite apenas se estiver incorreto.</div>
        </div>
        <div class="pending-ip-badges">${badges.join('')}</div>
      ` : ''}
    `
  }
}

function checkBlocked(v) {
  const l = String(v||'').toLowerCase()
  return BLOCKED_TERMS.some(t => l.includes(t))
}

function validateUnifiedInterfaceDescription(value) {
  const raw = String(value || '').trim()
  const parts = raw.split('|').map(part => part.trim())
  if (!raw) return 'Descricao proposta obrigatoria'
  if (parts.length !== 6 || parts.some(part => !part)) {
    return 'Use exatamente 6 campos separados por |: SVC|CID|HOST_REMOTO|PORTA_REMOTA|BANDA|COMENTARIO_OU_ROLE'
  }
  const svc = parts[0].toUpperCase()
  const cid = parts[1]
  const porta = parts[3]
  const banda = parts[4]
  const allowedSvc = ['CLI', 'OP', 'PTP', 'PTMP', 'EN']
  if (!allowedSvc.includes(svc)) return 'SVC deve ser CLI, OP, PTP, PTMP ou EN'
  const cidPatterns = {
    CLI: /^CID-\d+$/i,
    OP: /^OP-[A-Z0-9-]+$/i,
    PTP: /^L2-\d+$/i,
    PTMP: /^L2-\d+$/i,
    EN: /^CIR-\d+$/i,
  }
  if (!cidPatterns[svc].test(cid)) return `CID invalido para ${svc}`
  if (!/^[A-Z][A-Z0-9-]*\d+(?:\/\d+)*(?:\.\d+)?$/i.test(porta)) return 'PORTA_REMOTA invalida'
  if (!/^\d+(?:M|G|T)$/i.test(banda)) return 'BANDA deve terminar com M, G ou T'
  return ''
}

function validatePendingItemForm() {
  clearErrors(); hideModalMessage()
  const form = $('pending-item-form')
  if (!form || !state.item || !state.schema) return false
  const data = Object.fromEntries(new FormData(form).entries())
  const status = String(data.status||'').trim()
  let ok = true

  if (!data.updated_by || !String(data.updated_by).trim()) { setFieldError('updated_by','Responsável obrigatório'); ok=false }
  if (!status) { setFieldError('status','Status obrigatório'); ok=false }

  const reqOnAnswered = {
    subinterface: ['tenant','service_type','criticality','owner','evidence'],
    bgp_peer: ['remote_asn','remote_bgp_group','policy_intent','owner','criticality','evidence'],
  }
  const t = String(state.item.object_type||'').toLowerCase()
  const missingFields = (state.item.missing_fields || []).map(field => String(field).toLowerCase())
  const descriptionPending = ['interface', 'interface_description'].includes(t)
    && missingFields.some(field => ['description', 'descricao', 'proposed_description', 'description_naming', 'nomenclatura', 'nomenclatura_descricao', 'ajuste_nomenclatura'].includes(field))
  const reqFields = status==='answered' ? (reqOnAnswered[t]||[]) : []
  reqFields.forEach(f => { if (!String(data[f]||'').trim()) { setFieldError(f,`${f} obrigatório`); ok=false } })

  if (descriptionPending && status==='answered') {
    const error = validateUnifiedInterfaceDescription(data.proposed_description)
    if (error) { setFieldError('proposed_description', error); ok=false }
    if (!String(data.evidence||'').trim()) { setFieldError('evidence','Evidence obrigatorio'); ok=false }
  }

  if (t==='ip_address' && status==='answered') {
    if (!String(data.relation_type||'').trim()) { setFieldError('relation_type','Tipo de relação obrigatório'); ok=false }
    if (!String(data.interface||'').trim() && !String(state.item.detected_interface||'').trim()) { setFieldError('interface','Interface obrigatória'); ok=false }
    if (!String(data.vrf||'').trim() && !String(state.item.detected_vrf||'').trim()) { setFieldError('vrf','VRF obrigatória'); ok=false }
    if (String(data.relation_type||'')==='service' && !String(data.service_relation||'').trim()) { setFieldError('service_relation','Relação obrigatória'); ok=false }
    if (String(data.relation_type||'')==='unknown' && !String(data.notes||'').trim()) { setFieldError('notes','Observações obrigatórias'); ok=false }
  }
  if (['blocked','rejected','needs_clarification'].includes(status) && !String(data.notes||'').trim()) { setFieldError('notes','Observações obrigatórias'); ok=false }

  Object.entries(data).forEach(([f,v]) => { if (String(v||'').trim() && checkBlocked(v)) { setFieldError(f,`Campo contém termo bloqueado`); ok=false } })

  if (t==='bgp_peer' && data.remote_asn) {
    const asn = Number(data.remote_asn)
    if (!Number.isInteger(asn)||asn<1||asn>4294967295) { setFieldError('remote_asn','ASN deve estar entre 1 e 4294967295'); ok=false }
  }
  if (t==='ip_address' && data.interface) {
    const patterns = [/^Eth-Trunk\d+(\.\d+)?$/,/^GigabitEthernet\d+\/\d+\/\d+(\.\d+)?$/,/^10GE\d+\/\d+\/\d+$/,/^LoopBack\d+$/,/^Vlanif\d+$/]
    if (!patterns.some(p=>p.test(String(data.interface)))) { setFieldError('interface','Formato de interface inválido'); ok=false }
  }
  if (t==='ip_address' && data.vrf) {
    if (!/^(_public_|default|[a-zA-Z0-9_-]+)$/.test(String(data.vrf))) { setFieldError('vrf','Formato de VRF inválido'); ok=false }
  }
  return ok
}

function updateRowAfterSave(item, payload) {
  const row = $(`pending-row-${item.safe_item_id}`); if (!row) return
  const badge = $(`pending-status-${item.safe_item_id}`)
  if (badge) { badge.className = statusBadgeClass(payload.status); badge.textContent = payload.status }
  const missing = $(`missing-fields-${item.safe_item_id}`)
  if (missing) { missing.textContent = payload.status==='answered' ? 'nenhum' : (item.missing_fields||[]).join(', ')||'nenhum' }
  const button = $(`pending-button-${item.safe_item_id}`)
  if (button) { button.textContent = payload.status==='answered' ? 'Editar pendência' : 'Completar pendência' }
}

function updateValidationSummary(summary) {
  const keys = ['validated','ready_for_review','still_pending','needs_clarification','blocked','rejected']
  keys.forEach(k => {
    const el = $(`validation-count-${k}`)
    if (el && summary && k in summary) el.textContent = String(summary[k])
  })
}

function renderConventionViolations(violations) {
  if (!violations?.length) return ''
  const meta = {
    blocker: { icon:'🔒', cls:'danger', label:'BLOQUEADOR' },
    error:   { icon:'❌', cls:'danger', label:'ERRO' },
    warning: { icon:'⚠️', cls:'warning', label:'ALERTA' },
    info:    { icon:'ℹ️', cls:'info',    label:'INFO' },
  }
  const html = violations.map(v => {
    const m = meta[v.severity||'info'] || meta.info
    return `
      <div class="convention-violation alert alert-${m.cls}">
        <span class="alert-icon">${m.icon}</span>
        <div class="alert-body">
          <strong>${m.label} — ${escapeHtml(v.rule_id||'UNKNOWN')}</strong>
          ${escapeHtml(v.message_pt||v.message||'Violação detectada')}
        </div>
      </div>
    `
  }).join('')
  return `<div class="mt-16"><div class="text-muted" style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.7px;margin-bottom:8px;">Validação de Conformidade</div>${html}</div>`
}

async function openPendingItemModal(itemId, device) {
  state.device = device || state.device || document.body.dataset.device || ''
  if (!state.device) return
  hideModalMessage(); clearErrors()
  const url = `/service-engagement/${encodeURIComponent(state.device)}/pending-items/${encodeURIComponent(itemId)}`
  try {
    const res = await fetch(url, { headers: { Accept: 'application/json' } })
    const data = await res.json()
    if (!res.ok || !data.success) { setModalMessage(data.error||'Não foi possível carregar a pendência.','danger'); showModal(); return }
    state.item = data.item; state.schema = data.schema; state.safeItemId = itemId
    renderForm(data.schema, data.item); showModal()
  } catch (e) { setModalMessage('Erro de conexão.','danger'); showModal() }
}

function closePendingItemModal() { hideModal(); hideModalMessage(); clearErrors() }

async function runValidationNow(device) {
  const res = await fetch(`/service-engagement/${encodeURIComponent(device)}/responses/run-validation`, { method:'POST', headers:{Accept:'application/json'} })
  return res.json()
}

async function finalizeResponses(device) {
  const res = await fetch(`/service-engagement/${encodeURIComponent(device)}/responses/finalize`, { method:'POST', headers:{Accept:'application/json'} })
  return res.json()
}

async function submitPendingItemResponse(closeAfterSave, validateAfterSave) {
  if (!validatePendingItemForm()) { setModalMessage('Corrija os campos destacados antes de salvar.','warning'); return false }
  const form = $('pending-item-form')
  const payload = Object.fromEntries(new FormData(form).entries())
  const url = `/service-engagement/${encodeURIComponent(state.device)}/pending-items/${encodeURIComponent(state.safeItemId)}/response`
  const res = await fetch(url, { method:'POST', headers:{'Content-Type':'application/json',Accept:'application/json'}, body:JSON.stringify(payload) })
  const data = await res.json()
  const violations = data.convention_violations || []

  if (!res.ok || !data.success) {
    const errs = data.errors || [data.error||'Falha ao salvar.']
    const helper = $('pending-item-modal-message')
    if (helper) {
      helper.innerHTML = `<div>${errs.map(e=>`<div>${escapeHtml(e)}</div>`).join('')}</div>${renderConventionViolations(violations)}`
      helper.className = 'alert alert-danger'; helper.classList.remove('hidden')
    }
    return false
  }

  updateRowAfterSave(state.item, payload)
  if (data.pipeline?.validation) updateValidationSummary(data.pipeline.validation)

  const helper = $('pending-item-modal-message')
  if (helper) {
    const remaining = data.pipeline?.validation ? Number(data.pipeline.validation.still_pending||0) : 0
    helper.innerHTML = `
      <div>${escapeHtml(data.message)}</div>
      <div class="mono text-secondary" style="font-size:11px;margin-top:4px;">${escapeHtml(data.csv_path)}</div>
      <div style="margin-top:6px;">${remaining>0 ? `Ainda existem <strong>${remaining}</strong> pendências.` : '✅ Todas as pendências foram respondidas.'}</div>
      ${renderConventionViolations(violations)}
      <div class="pending-validation-links">
        <a class="btn btn-sm btn-secondary" href="/reports/download?path=${escapeHtml(data.csv_path)}">📄 Ver CSV</a>
        <a class="btn btn-sm btn-secondary" href="/service-engagement/${encodeURIComponent(state.device)}/validation">🔍 Ver validação</a>
        ${data.pipeline?.week2_prepared ? `<a class="btn btn-sm btn-accent" href="/service-engagement/${encodeURIComponent(state.device)}/week2-review">→ Semana 2</a>` : ''}
      </div>
    `
    helper.className = 'alert alert-success'; helper.classList.remove('hidden')
  }

  showToast(data.message, 'success')
  if (closeAfterSave) { closePendingItemModal(); window.location.reload() }
  if (validateAfterSave) {
    const v = await runValidationNow(state.device)
    if (v?.validation) updateValidationSummary(v.validation)
  }
  return true
}

async function finalizeResponsesAndRefresh(device) {
  const result = await finalizeResponses(device || state.device || document.body.dataset.device || '')
  if (!result?.success) { setModalMessage(result?.error||'Falha ao finalizar respostas.','danger'); return false }
  if (result.validation) updateValidationSummary(result.validation)
  showToast(result.next_action||'Validação executada.', 'success')
  window.location.reload()
  return true
}

async function refreshComplianceQuery(jobId) {
  if (!jobId) {
    showToast('Nenhum job de compliance encontrado para este dispositivo.', 'warning')
    return false
  }
  const confirmed = window.confirm('Executar nova coleta real SSH read-only, novo parser e nova comparação de compliance?')
  if (!confirmed) return false

  const button = $('refresh-compliance-query-btn')
  const status = $('refresh-compliance-query-status')
  if (button) button.disabled = true
  if (status) status.textContent = 'Atualizando consulta...'

  try {
    const response = await fetch(`/compliance/jobs/${encodeURIComponent(jobId)}/refresh-query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ operator: 'Keslley', confirm_refresh_read_only: true }),
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok || !data.success) {
      const detail = (data.steps || []).map(step => `${step.step}: ${step.decision}`).join(' | ')
      const message = `${data.error || 'Falha ao atualizar consulta de compliance'}${detail ? ` (${detail})` : ''}`
      if (status) status.textContent = 'Falha na atualização.'
      showToast(message, 'danger', 8000)
      return false
    }
    if (status) status.textContent = 'Consulta atualizada.'
    showToast('Consulta de compliance atualizada.', 'success')
    window.location.reload()
    return true
  } catch (error) {
    if (status) status.textContent = 'Falha na atualização.'
    showToast(`Falha ao atualizar consulta de compliance: ${error.message}`, 'danger', 8000)
    return false
  } finally {
    if (button) button.disabled = false
  }
}

function togglePendingItemDetail(id) {
  const el = $(id); if (el) el.classList.toggle('hidden')
}

// ── Expose globals (backward compat) ─────────────────────
window.openPendingItemModal = openPendingItemModal
window.closePendingItemModal = closePendingItemModal
window.validatePendingItemForm = validatePendingItemForm
window.submitPendingItemResponse = submitPendingItemResponse
window.runValidationNow = runValidationNow
window.finalizeResponsesAndRefresh = finalizeResponsesAndRefresh
window.refreshComplianceQuery = refreshComplianceQuery
window.togglePendingItemDetail = togglePendingItemDetail
window.showToast = showToast

// ── Init ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  setActiveNav()
  initSearch()
})
