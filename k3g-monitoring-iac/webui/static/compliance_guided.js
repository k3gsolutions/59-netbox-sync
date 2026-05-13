/* =============================================================
   compliance.js — Guided Compliance Wizard
   ============================================================= */

// ── Config ──────────────────────────────────────────────────────
let API_BASE = localStorage.getItem('api_base') || '';
let API_KEY  = localStorage.getItem('api_key')  || '';

if (API_BASE === '/compliance/guided' || (window.location.protocol === 'https:' && API_BASE.startsWith('http://'))) {
  API_BASE = '';
  localStorage.removeItem('api_base');
}

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
  analysisMode: null,  // 'netbox' | 'file'
  selectedTenant: null,
  selectedDevice: null,
  allDevices: [],
  selectedDeviceType: 'all',
  selectedContexts: new Set(),
  allContexts: [],
  findings: [],
  analysisResult: null,
  // File mode
  fileData: {
    platform: 'huawei',
    deviceName: '',
    file: null,
  },
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

// ── Mode Selection (Step 0) ─────────────────────────────────────
function showModeChoice() {
  show('mode-choice-modal');
}

function selectMode(mode) {
  state.analysisMode = mode;
  hide('mode-choice-modal');
  if (mode === 'netbox') {
    loadTenants();
  } else if (mode === 'file') {
    showFileUploadStep();
  }
}

async function showFileUploadStep() {
  // Hide all normal steps
  [1,2,3,4].forEach(i => hide(`step-${i}`));
  // Load contexts for file mode
  await loadFileContexts();
  // Show file upload UI
  show('step-file-upload');
  // Reset contexts for file mode
  state.selectedContexts.clear();
  $('btn-file-analyze').disabled = true;
  // Automatically open the file picker
  const fileInput = document.getElementById('file-config-input');
  if (fileInput) fileInput.click();
}

async function loadFileContexts() {
  try {
    const contexts = await apiFetch('/compliance/eligible-contexts');
    const grid = $('file-contexts-grid');
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
      card.addEventListener('click', () => {
        toggleFileContext(card);
      });
    });
  } catch (err) {
    console.error('Failed to load file contexts:', err);
  }
}

function toggleFileContext(card) {
  const id = card.dataset.id;
  if (state.selectedContexts.has(id)) {
    state.selectedContexts.delete(id);
    card.classList.remove('selected');
  } else {
    state.selectedContexts.add(id);
    card.classList.add('selected');
  }
  $('btn-file-analyze').disabled = state.selectedContexts.size === 0;
}

async function runFileAnalysis() {
  const platform = $('file-platform-select')?.value || 'huawei';
  const deviceName = $('file-device-name')?.value || 'file-analysis';
  const fileInput = $('file-config-input');
  const file = fileInput?.files?.[0];

  if (!file) {
    alert('Selecione um arquivo .txt, .csv ou .json');
    return;
  }

  if (state.selectedContexts.size === 0) {
    alert('Selecione pelo menos um contexto');
    return;
  }

  show('file-upload-loading');
  hide('file-upload-error');
  $('file-results-info').innerHTML = '';
  $('file-findings-tbody').innerHTML = '';

  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('platform', platform);
    formData.append('device_name', deviceName);
    formData.append('contexts', JSON.stringify([...state.selectedContexts]));

    const res = await fetch(`${API_BASE}/compliance/analyze-file`, {
      method: 'POST',
      headers: API_KEY ? { 'X-API-Key': API_KEY } : {},
      body: formData,
    });

    if (!res.ok) {
      const body = await res.json();
      throw new Error(body.detail || `HTTP ${res.status}`);
    }

    const result = await res.json();
    state.analysisResult = result;
    state.findings = result.findings || [];

    hide('file-upload-loading');
    goToFileResultsStep(result);

  } catch (err) {
    hide('file-upload-loading');
    $('file-upload-error').textContent = `❌ Erro: ${err.message}`;
    show('file-upload-error');
  }
}

function goToFileResultsStep(result) {
  hide('step-file-upload');
  show('step-file-results');

  // Results header
  const statusLabel = { ok: '✅ Conformidade OK', attention: '⚠️ Requer atenção', failed: '❌ Não conforme' };
  $('file-results-device-name').textContent = `📄 ${escHtml(result.device)}`;
  $('file-results-status').textContent = `Análise de arquivo (${result.platform}) · ${statusLabel[result.status] || result.status}`;

  // Summary cards
  const s = result.summary;
  $('file-results-summary').innerHTML = `
    <div class="summary-card summary-approved"><span class="summary-icon">✅</span><div><div class="summary-count">${s.approved}</div><div class="summary-label">Aprovados</div></div></div>
    <div class="summary-card summary-warning"><span class="summary-icon">⚠️</span><div><div class="summary-count">${s.warning}</div><div class="summary-label">Atenção</div></div></div>
    <div class="summary-card summary-failed"><span class="summary-icon">❌</span><div><div class="summary-count">${s.failed}</div><div class="summary-label">Reprovados</div></div></div>
  `;

  // Collection notes
  if (result.collection_notes?.length) {
    $('file-notes-list').innerHTML = result.collection_notes
      .filter(n => !n.includes('⚠'))
      .map(n => `<li>${escHtml(n)}</li>`).join('');
    show('file-collection-notes-box');
  }

  // Findings
  const total = s.warning + s.failed;
  $('file-findings-count-title').textContent = total > 0
    ? `Encontramos ${total} ponto${total !== 1 ? 's' : ''} que precisam de atenção.`
    : 'Todos os itens analisados estão em conformidade. ✅';

  renderFileFindings('all');
}

function renderFileFindings(filter) {
  const tbody = $('file-findings-tbody');
  let list = state.findings;
  if (filter !== 'all') list = list.filter(f => f.status === filter);

  if (!list.length) {
    tbody.innerHTML = '';
    show('file-findings-empty');
    return;
  }
  hide('file-findings-empty');

  tbody.innerHTML = list.map((f, idx) => `
    <div class="finding-card finding-${f.status}" data-idx="${idx}">
      <div class="finding-card-header">
        <div class="finding-card-badges">
          ${badgeHtml(f.status)}
          <span class="finding-context-badge">${escHtml(f.context)}</span>
        </div>
      </div>
      <div class="finding-card-body">
        <h4 class="finding-card-title">${escHtml(f.title)}</h4>
        <div class="finding-card-item"><span class="mono">${escHtml(f.item)}</span></div>
      </div>
      <div class="finding-card-footer">
        <div class="finding-card-source">Origem: ${escHtml(f.source || 'Local')}</div>
        <button class="btn btn-ghost btn-sm btn-detail" data-finding-idx="${idx}">[ Ver detalhes ]</button>
      </div>
    </div>
  `).join('');

  tbody.querySelectorAll('.btn-detail').forEach(btn => {
    btn.addEventListener('click', () => openDetail(+btn.dataset.findingIdx));
  });
}

// ── API status check ─────────────────────────────────────────────
async function checkApiStatus() {
  try {
    await apiFetch('/health');
    if ($('dot')) $('dot').className = 'status-dot ok';
    if ($('api-status-label')) $('api-status-label').textContent = 'API online';
    return true;
  } catch {
    if ($('dot')) $('dot').className = 'status-dot error';
    if ($('api-status-label')) $('api-status-label').textContent = 'API offline';
    return false;
  }
}

function updateApiUrlBadge() {
  const host = API_BASE ? new URL(API_BASE).host : window.location.host;
  $('api-url-badge').innerHTML = `<span class="mono">${host}</span>`;
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
  hide('devices-empty');
  hide('device-type-filter');
  state.allDevices = [];
  state.selectedDeviceType = 'all';

  try {
    const devices = await apiFetch(`/compliance/eligible-devices?tenant_id=${tenantId}`);
    hide('devices-loading');

    if (!devices.length) {
      $('devices-error').textContent = '⚠️ Nenhum dispositivo elegível encontrado para este cliente.';
      show('devices-error');
      return;
    }

    state.allDevices = devices;
    populateDeviceTypeFilter(devices);
    renderDeviceList();
    show('device-type-filter');
  } catch (err) {
    hide('devices-loading');
    $('devices-error').textContent = `❌ Erro ao carregar dispositivos: ${err.message}`;
    show('devices-error');
  }
}

function getDeviceFunction(device) {
  return device.role || 'Sem função informada';
}

function populateDeviceTypeFilter(devices) {
  const select = $('device-type-select');
  const counts = new Map();
  devices.forEach(d => {
    const type = getDeviceFunction(d);
    counts.set(type, (counts.get(type) || 0) + 1);
  });

  select.innerHTML = '';

  const allOption = document.createElement('option');
  allOption.value = 'all';
  allOption.textContent = `Todas as funções (${devices.length})`;
  select.appendChild(allOption);

  [...counts.entries()]
    .sort(([a], [b]) => a.localeCompare(b, 'pt-BR'))
    .forEach(([type, count]) => {
      const option = document.createElement('option');
      option.value = type;
      option.textContent = `${type} (${count})`;
      select.appendChild(option);
    });

  select.value = 'all';
  $('device-filter-count').textContent = `${devices.length} dispositivo${devices.length !== 1 ? 's' : ''}`;
}

function renderDeviceList() {
  const filteredDevices = state.selectedDeviceType === 'all'
    ? state.allDevices
    : state.allDevices.filter(d => getDeviceFunction(d) === state.selectedDeviceType);

  $('device-filter-count').textContent = `${filteredDevices.length} dispositivo${filteredDevices.length !== 1 ? 's' : ''}`;

  if (!filteredDevices.length) {
    hide('devices-list');
    show('devices-empty');
    return;
  }

  hide('devices-empty');

  const list = $('devices-list');
  list.innerHTML = filteredDevices.map(d => `
      <div class="device-card" data-id="${d.id}" data-name="${escHtml(d.name)}">
        <div class="device-icon">🖥️</div>
        <div class="device-info">
          <div class="device-name">${escHtml(d.name)}</div>
          <div class="device-meta">
            ${d.role ? escHtml(d.role) : ''}${d.manufacturer ? ' · ' + escHtml(d.manufacturer) : ''}${d.model ? ' · ' + escHtml(d.model) : ''}${d.site ? ' · ' + escHtml(d.site) : ''}
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
    const contexts = await apiFetch('/compliance/eligible-contexts');
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
    <div class="finding-card finding-${f.status}" data-idx="${idx}">
      <div class="finding-card-header">
        <div class="finding-card-badges">
          ${badgeHtml(f.status)}
          <span class="finding-context-badge">${escHtml(f.context)}</span>
        </div>
      </div>
      <div class="finding-card-body">
        <h4 class="finding-card-title">${escHtml(f.title)}</h4>
        <div class="finding-card-item"><span class="mono">${escHtml(f.item)}</span></div>
      </div>
      <div class="finding-card-footer">
        <div class="finding-card-source">Origem: ${escHtml(f.source || 'N/A')}</div>
        <button class="btn btn-ghost btn-sm btn-detail" data-finding-idx="${findingGlobalIdx(f)}">[ Ver detalhes ]</button>
      </div>
    </div>
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
  API_BASE = url;
  API_KEY  = key;
  if (url) {
    localStorage.setItem('api_base', url);
  } else {
    localStorage.removeItem('api_base');
  }
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

// ── Mode Choice Close ────────────────────────────────────────────
function closeModeChoice() {
  hide('mode-choice-modal');
}

// ── Event Listeners ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  try {
    // Initial load — guard against missing elements
    if ($('api-url-badge')) updateApiUrlBadge();
    const urlInput = $('input-api-url');
    const keyInput = $('input-api-key');
    if (urlInput) urlInput.value = API_BASE;
    if (keyInput) keyInput.value = API_KEY;
    checkApiStatus();
  } catch(e) {
    console.warn('[compliance] init error (non-fatal):', e);
  }

  // Show mode choice modal
  showModeChoice();

  const deviceTypeSelect = $('device-type-select');
  if (deviceTypeSelect) {
    deviceTypeSelect.addEventListener('change', (event) => {
      state.selectedDeviceType = event.target.value;
      state.selectedDevice = null;
      renderDeviceList();
    });
  }

  // Step navigation — use ?. so missing elements don't crash all listeners
  $('back-to-step1')?.addEventListener('click', () => goToStep(1));
  $('back-to-step2')?.addEventListener('click', () => goToStep(2));
  $('back-to-step3')?.addEventListener('click', () => goToStep(3));
  $('btn-analyze')?.addEventListener('click', runAnalysis);
  $('btn-new-analysis')?.addEventListener('click', () => {
    state.selectedContexts.clear();
    goToStep(1);
    loadTenants();
  });

  // Make step indicators clickable to go back
  [1, 2, 3, 4].forEach(i => {
    const ind = $('step-ind-' + i);
    if (ind) {
      ind.addEventListener('click', () => {
        if (ind.classList.contains('done') || ind.classList.contains('active')) {
          goToStep(i);
        }
      });
    }
  });

  // Context select/deselect all
  $('select-all-ctx')?.addEventListener('click', () => {
    document.querySelectorAll('.context-card').forEach(card => {
      card.classList.add('selected');
      state.selectedContexts.add(card.dataset.id);
    });
    if ($('btn-analyze')) $('btn-analyze').disabled = false;
  });
  $('deselect-all-ctx')?.addEventListener('click', () => {
    document.querySelectorAll('.context-card').forEach(card => card.classList.remove('selected'));
    state.selectedContexts.clear();
    if ($('btn-analyze')) $('btn-analyze').disabled = true;
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
  $('btn-settings')?.addEventListener('click', openSettings);
  $('close-settings')?.addEventListener('click', closeSettings);
  $('cancel-settings')?.addEventListener('click', closeSettings);
  $('save-settings')?.addEventListener('click', saveSettings);

  // Detail modal
  $('close-detail')?.addEventListener('click', closeDetail);
  $('close-detail-btn')?.addEventListener('click', closeDetail);

  // Close modals on overlay click
  $('settings-modal')?.addEventListener('click', e => { if (e.target.id === 'settings-modal') closeSettings(); });
  $('detail-modal')?.addEventListener('click', e => { if (e.target.id === 'detail-modal') closeDetail(); });

  // Mode choice buttons
  $('mode-btn-netbox')?.addEventListener('click', () => selectMode('netbox'));
  $('mode-btn-file')?.addEventListener('click', () => selectMode('file'));
  $('mode-choice-close')?.addEventListener('click', closeModeChoice);
  // Close on overlay click
  $('mode-choice-modal')?.addEventListener('click', e => { if (e.target.id === 'mode-choice-modal') closeModeChoice(); });

  // File upload form
  $('file-platform-select')?.addEventListener('change', (e) => {
    state.fileData.platform = e.target.value;
  });

  $('file-device-name')?.addEventListener('input', (e) => {
    state.fileData.deviceName = e.target.value;
  });

  $('file-config-input')?.addEventListener('change', (e) => {
    state.fileData.file = e.target.files?.[0] || null;
    const name = state.fileData.file?.name || 'Nenhum arquivo selecionado';
    $('file-input-name').textContent = name;
  });

  // File upload contexts select all/deselect all
  $('file-select-all-ctx')?.addEventListener('click', () => {
    document.querySelectorAll('#file-contexts-grid .context-card').forEach(card => {
      card.classList.add('selected');
      state.selectedContexts.add(card.dataset.id);
    });
    $('btn-file-analyze').disabled = false;
  });

  $('file-deselect-all-ctx')?.addEventListener('click', () => {
    document.querySelectorAll('#file-contexts-grid .context-card').forEach(card => {
      card.classList.remove('selected');
      state.selectedContexts.delete(card.dataset.id);
    });
    $('btn-file-analyze').disabled = true;
  });

  // File analyze button
  $('btn-file-analyze')?.addEventListener('click', runFileAnalysis);

  // File upload: back button
  $('back-to-mode-choice')?.addEventListener('click', () => {
    state.analysisMode = null;
    state.selectedContexts.clear();
    hide('step-file-upload');
    show('mode-choice-modal');
  });

  // File results: filter buttons
  document.querySelectorAll('#step-file-results .filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#step-file-results .filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderFileFindings(btn.dataset.filter);
    });
  });

  // File results: new analysis button
  $('btn-file-new-analysis')?.addEventListener('click', () => {
    state.analysisMode = null;
    state.selectedContexts.clear();
    state.findings = [];
    hide('step-file-results');
    showModeChoice();
  });

  // ESC key
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') { closeDetail(); closeSettings(); closeModeChoice(); }
  });
});
