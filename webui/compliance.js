/* =============================================================
   compliance.js — Guided Compliance Wizard
   ============================================================= */

// ── Config ──────────────────────────────────────────────────────
let API_BASE = localStorage.getItem('api_base') || 'http://localhost:8888';
let API_KEY  = localStorage.getItem('api_key')  || '';

function apiHeaders() {
  const h = { 'Content-Type': 'application/json', 'Accept': 'application/json' };
  if (API_KEY) h['X-API-Key'] = API_KEY;
  return h;
}

async function apiFetch(path, opts = {}) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, { headers: apiHeaders(), ...opts });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── State ────────────────────────────────────────────────────────
let state = {
  currentStep: 1,
  selectedTenant: null,
  selectedDevice: null,
  selectedContexts: new Set(),
  allContexts: [],
  findings: [],
  analysisResult: null,
};

// ── DOM refs ─────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const show = id => $(`${id}`)?.classList.remove('hidden');
const hide = id => $(`${id}`)?.classList.add('hidden');

// ── Step management ──────────────────────────────────────────────
function goToStep(n) {
  [1,2,3,4].forEach(i => {
    document.getElementById(`step-${i}`)?.classList.add('hidden');
    const ind = document.getElementById(`step-ind-${i}`);
    if (ind) {
      ind.classList.remove('active','done');
      if (i < n) ind.classList.add('done');
      if (i === n) ind.classList.add('active');
    }
  });
  // Update step-lines
  document.querySelectorAll('.step-line').forEach((line, idx) => {
    line.classList.toggle('done', idx + 1 < n);
  });
  show(`step-${n}`);
  state.currentStep = n;
}

// ── API status check ─────────────────────────────────────────────
async function checkApiStatus() {
  try {
    await apiFetch('/health');
    $('dot').className = 'status-dot ok';
    $('api-status-label').textContent = 'API online';
    return true;
  } catch {
    $('dot').className = 'status-dot error';
    $('api-status-label').textContent = 'API offline';
    return false;
  }
}

function updateApiUrlBadge() {
  const url = new URL(API_BASE);
  $('api-url-badge').innerHTML = `<span class="mono">${url.host}</span>`;
}

// ── STEP 1: Tenants ──────────────────────────────────────────────
async function loadTenants() {
  show('tenants-loading');
  hide('tenants-error');
  hide('tenants-grid');

  try {
    const tenants = await apiFetch('/compliance/eligible-tenants');
    hide('tenants-loading');

    if (!tenants.length) {
      $('tenants-error').textContent = '⚠️ Nenhum cliente elegível encontrado. Verifique se há dispositivos com Compliance habilitado no Tenant Group K3G Solutions.';
      show('tenants-error');
      return;
    }

    const grid = $('tenants-grid');
    grid.innerHTML = tenants.map(t => `
      <div class="tenant-card" data-id="${t.id}" data-name="${escHtml(t.name)}" data-slug="${t.slug}">
        <div class="tenant-card-name">🏢 ${escHtml(t.name)}</div>
        <div class="tenant-card-count">${t.device_count} dispositivo${t.device_count !== 1 ? 's' : ''} elegível${t.device_count !== 1 ? 'is' : ''}</div>
        ${t.description ? `<div class="tenant-card-desc">${escHtml(t.description)}</div>` : ''}
      </div>
    `).join('');

    grid.querySelectorAll('.tenant-card').forEach(card => {
      card.addEventListener('click', () => selectTenant(card));
    });

    show('tenants-grid');
  } catch (err) {
    hide('tenants-loading');
    $('tenants-error').textContent = `❌ Erro ao carregar clientes: ${err.message}`;
    show('tenants-error');
  }
}

function selectTenant(card) {
  document.querySelectorAll('.tenant-card').forEach(c => c.classList.remove('selected'));
  card.classList.add('selected');
  state.selectedTenant = { id: +card.dataset.id, name: card.dataset.name };
  setTimeout(() => loadDevices(state.selectedTenant.id), 200);
}

// ── STEP 2: Devices ──────────────────────────────────────────────
async function loadDevices(tenantId) {
  goToStep(2);
  $('selected-tenant-chip').innerHTML = `🏢 ${escHtml(state.selectedTenant.name)}`;
  show('devices-loading');
  hide('devices-error');
  hide('devices-list');

  try {
    const devices = await apiFetch(`/compliance/eligible-devices?tenant_id=${tenantId}`);
    hide('devices-loading');

    if (!devices.length) {
      $('devices-error').textContent = '⚠️ Nenhum dispositivo elegível encontrado para este cliente.';
      show('devices-error');
      return;
    }

    const list = $('devices-list');
    list.innerHTML = devices.map(d => `
      <div class="device-card" data-id="${d.id}" data-name="${escHtml(d.name)}">
        <div class="device-icon">🖥️</div>
        <div class="device-info">
          <div class="device-name">${escHtml(d.name)}</div>
          <div class="device-meta">
            ${d.manufacturer ? escHtml(d.manufacturer) : ''}${d.model ? ' · ' + escHtml(d.model) : ''}${d.site ? ' · ' + escHtml(d.site) : ''}
          </div>
          ${d.primary_ip ? `<div class="device-ip">${escHtml(d.primary_ip)}</div>` : ''}
        </div>
        <div class="device-badge">✅ Compliance</div>
      </div>
    `).join('');

    list.querySelectorAll('.device-card').forEach(card => {
      card.addEventListener('click', () => selectDevice(card));
    });

    show('devices-list');
  } catch (err) {
    hide('devices-loading');
    $('devices-error').textContent = `❌ Erro ao carregar dispositivos: ${err.message}`;
    show('devices-error');
  }
}

function selectDevice(card) {
  document.querySelectorAll('.device-card').forEach(c => c.classList.remove('selected'));
  card.classList.add('selected');
  state.selectedDevice = { id: +card.dataset.id, name: card.dataset.name };
  setTimeout(() => loadContexts(state.selectedDevice.id), 200);
}

// ── STEP 3: Contexts ─────────────────────────────────────────────
async function loadContexts(deviceId) {
  goToStep(3);
  $('selected-device-chip').innerHTML = `🖥️ ${escHtml(state.selectedDevice.name)}`;
  state.selectedContexts.clear();
  show('contexts-loading');
  hide('contexts-error');
  hide('contexts-grid');
  hide('context-actions');
  $('btn-analyze').disabled = true;

  try {
    const contexts = await apiFetch(`/compliance/contexts?device_id=${deviceId}`);
    state.allContexts = contexts;
    hide('contexts-loading');

    const grid = $('contexts-grid');
    const methodLabel = { snmp: 'SNMP', ssh: 'SSH', netbox: 'NetBox' };
    const methodClass = { snmp: 'method-snmp', ssh: 'method-ssh', netbox: 'method-netbox' };

    grid.innerHTML = contexts.map(ctx => `
      <div class="context-card" data-id="${ctx.id}">
        <div class="context-card-top">
          <span class="context-icon">${ctx.icon}</span>
          <span class="context-label">${escHtml(ctx.label)}</span>
        </div>
        <div class="context-desc">${escHtml(ctx.description)}</div>
        <span class="context-method ${methodClass[ctx.collection_method] || 'method-netbox'}">
          via ${methodLabel[ctx.collection_method] || ctx.collection_method}
        </span>
      </div>
    `).join('');

    grid.querySelectorAll('.context-card').forEach(card => {
      card.addEventListener('click', () => toggleContext(card));
    });

    show('contexts-grid');
    show('context-actions');
  } catch (err) {
    hide('contexts-loading');
    $('contexts-error').textContent = `❌ Erro ao carregar contextos: ${err.message}`;
    show('contexts-error');
  }
}

function toggleContext(card) {
  const id = card.dataset.id;
  if (state.selectedContexts.has(id)) {
    state.selectedContexts.delete(id);
    card.classList.remove('selected');
  } else {
    state.selectedContexts.add(id);
    card.classList.add('selected');
  }
  $('btn-analyze').disabled = state.selectedContexts.size === 0;
}

// ── STEP 4: Analysis ─────────────────────────────────────────────
async function runAnalysis() {
  goToStep(4);

  // Device info header
  $('results-device-info').innerHTML = `
    <div class="results-device-name">🖥️ ${escHtml(state.selectedDevice.name)}</div>
    <div class="results-device-meta">Cliente: ${escHtml(state.selectedTenant.name)} · Análise em andamento...</div>
  `;
  $('results-summary').innerHTML = '';
  hide('collection-notes-box');
  $('findings-tbody').innerHTML = '';
  hide('findings-empty');
  show('findings-loading');
  hide('findings-error');

  const ctxLabels = {};
  state.allContexts.forEach(c => { ctxLabels[c.id] = c.label; });

  try {
    const result = await apiFetch('/compliance/analyze-guided', {
      method: 'POST',
      body: JSON.stringify({
        tenant_id: state.selectedTenant.id,
        device_id: state.selectedDevice.id,
        contexts: [...state.selectedContexts],
      }),
    });

    state.analysisResult = result;
    state.findings = result.findings || [];
    hide('findings-loading');

    // Update header
    const statusLabel = { ok: '✅ Conformidade OK', attention: '⚠️ Requer atenção', failed: '❌ Não conforme' };
    $('results-device-info').innerHTML = `
      <div class="results-device-name">🖥️ ${escHtml(result.device)}</div>
      <div class="results-device-meta">Cliente: ${escHtml(result.tenant)} · ${statusLabel[result.status] || result.status}</div>
    `;

    // Summary cards
    const s = result.summary;
    $('results-summary').innerHTML = `
      <div class="summary-card summary-approved"><span class="summary-icon">✅</span><div><div class="summary-count">${s.approved}</div><div class="summary-label">Aprovados</div></div></div>
      <div class="summary-card summary-warning"><span class="summary-icon">⚠️</span><div><div class="summary-count">${s.warning}</div><div class="summary-label">Atenção</div></div></div>
      <div class="summary-card summary-failed"><span class="summary-icon">❌</span><div><div class="summary-count">${s.failed}</div><div class="summary-label">Reprovados</div></div></div>
    `;

    // Collection notes
    if (result.collection_notes?.length) {
      $('notes-list').innerHTML = result.collection_notes.map(n => `<li>${escHtml(n)}</li>`).join('');
      show('collection-notes-box');
    }

    // Human summary text
    const total = s.warning + s.failed;
    $('findings-count-title').textContent = total > 0
      ? `Encontramos ${total} ponto${total !== 1 ? 's' : ''} que precisam de atenção neste dispositivo.`
      : 'Todos os itens analisados estão em conformidade. ✅';

    renderFindings('all');

  } catch (err) {
    hide('findings-loading');
    $('findings-error').textContent = `❌ Erro na análise: ${err.message}`;
    show('findings-error');
  }
}

function renderFindings(filter) {
  const tbody = $('findings-tbody');
  let list = state.findings;
  if (filter !== 'all') list = list.filter(f => f.status === filter);

  if (!list.length) {
    tbody.innerHTML = '';
    show('findings-empty');
    return;
  }
  hide('findings-empty');

  tbody.innerHTML = list.map((f, idx) => `
    <tr data-idx="${idx}" data-status="${f.status}" class="finding-row ${filter === 'all' ? '' : ''}">
      <td class="col-status">${badgeHtml(f.status)}</td>
      <td class="col-context">${escHtml(f.context)}</td>
      <td class="col-item">${escHtml(f.item)}</td>
      <td class="col-summary">${escHtml(f.title)}</td>
      <td class="col-action">
        <button class="btn btn-ghost btn-sm btn-detail" data-finding-idx="${findingGlobalIdx(f)}">Ver detalhes</button>
      </td>
    </tr>
  `).join('');

  tbody.querySelectorAll('.btn-detail').forEach(btn => {
    btn.addEventListener('click', () => openDetail(+btn.dataset.findingIdx));
  });
}

function findingGlobalIdx(finding) {
  return state.findings.indexOf(finding);
}

function badgeHtml(status) {
  const map = {
    approved: '<span class="badge badge-approved">✅ Aprovado</span>',
    warning:  '<span class="badge badge-warning">⚠️ Atenção</span>',
    failed:   '<span class="badge badge-failed">❌ Reprovado</span>',
  };
  return map[status] || `<span class="badge">${status}</span>`;
}

// ── Detail Modal ─────────────────────────────────────────────────
function openDetail(idx) {
  const f = state.findings[idx];
  if (!f) return;

  $('detail-badge').innerHTML = badgeHtml(f.status);
  $('detail-title').textContent = f.title;

  function detailRow(elId, label, value, mono = false) {
    if (!value) { $(`d-${elId}`).innerHTML = ''; return; }
    $(`d-${elId}`).innerHTML = `
      <div class="detail-label">${label}</div>
      <div class="detail-value${mono ? ' mono' : ''}">${escHtml(String(value))}</div>
    `;
  }

  detailRow('context', 'Contexto', f.context);
  detailRow('item', 'Item analisado', f.item, true);
  detailRow('expected', 'Valor esperado', f.expected, true);
  detailRow('found', 'Valor encontrado', f.found, true);
  detailRow('impact', 'Impacto', f.impact);
  detailRow('recommendation', 'Sugestão de correção', f.recommendation);
  detailRow('source', 'Origem da coleta', f.source);
  detailRow('evidence', 'Evidência', f.evidence, true);

  show('detail-modal');
}

function closeDetail() { hide('detail-modal'); }

// ── Settings Modal ───────────────────────────────────────────────
function openSettings() { show('settings-modal'); }
function closeSettings() { hide('settings-modal'); }

async function saveSettings() {
  const url = $('input-api-url').value.trim().replace(/\/$/, '');
  const key  = $('input-api-key').value.trim();
  if (!url) return;
  API_BASE = url;
  API_KEY  = key;
  localStorage.setItem('api_base', url);
  localStorage.setItem('api_key', key);
  updateApiUrlBadge();
  closeSettings();
  await checkApiStatus();
  loadTenants();
}

// ── Utilities ─────────────────────────────────────────────────────
function escHtml(s) {
  if (!s) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Event Listeners ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Initial load
  updateApiUrlBadge();
  $('input-api-url').value = API_BASE;
  $('input-api-key').value = API_KEY;
  checkApiStatus();
  loadTenants();

  // Step navigation
  $('back-to-step1').addEventListener('click', () => goToStep(1));
  $('back-to-step2').addEventListener('click', () => goToStep(2));
  $('back-to-step3').addEventListener('click', () => goToStep(3));
  $('btn-analyze').addEventListener('click', runAnalysis);
  $('btn-new-analysis').addEventListener('click', () => {
    state.selectedContexts.clear();
    goToStep(1);
    loadTenants();
  });

  // Make step indicators clickable to go back
  [1, 2, 3, 4].forEach(i => {
    const ind = $('step-ind-' + i);
    if (ind) {
      ind.addEventListener('click', () => {
        // Allow navigating to any previously completed step
        if (ind.classList.contains('done') || ind.classList.contains('active')) {
          goToStep(i);
        }
      });
    }
  });

  // Context select/deselect all
  $('select-all-ctx').addEventListener('click', () => {
    document.querySelectorAll('.context-card').forEach(card => {
      card.classList.add('selected');
      state.selectedContexts.add(card.dataset.id);
    });
    $('btn-analyze').disabled = false;
  });
  $('deselect-all-ctx').addEventListener('click', () => {
    document.querySelectorAll('.context-card').forEach(card => card.classList.remove('selected'));
    state.selectedContexts.clear();
    $('btn-analyze').disabled = true;
  });

  // Filter buttons
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderFindings(btn.dataset.filter);
    });
  });

  // Settings
  $('btn-settings').addEventListener('click', openSettings);
  $('close-settings').addEventListener('click', closeSettings);
  $('cancel-settings').addEventListener('click', closeSettings);
  $('save-settings').addEventListener('click', saveSettings);

  // Detail modal
  $('close-detail').addEventListener('click', closeDetail);
  $('close-detail-btn').addEventListener('click', closeDetail);

  // Close modals on overlay click
  $('settings-modal').addEventListener('click', e => { if (e.target.id === 'settings-modal') closeSettings(); });
  $('detail-modal').addEventListener('click', e => { if (e.target.id === 'detail-modal') closeDetail(); });

  // ESC key
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') { closeDetail(); closeSettings(); }
  });
});
