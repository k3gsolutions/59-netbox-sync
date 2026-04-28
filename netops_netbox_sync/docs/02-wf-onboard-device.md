# wf-onboard-device

Provisiona/atualiza/desabilita host Zabbix com base em evento NetBox `dcim.device`.

**Acionado por:** `wf-netbox-router` (Execute Workflow).

**Princípio:** idempotente. Resolve estado desejado via NetBox + role_template_map. Compara com estado atual no Zabbix. Aplica diff.

---

## Input esperado (do router)

```json
{
  "correlation_id": "uuid",
  "event": "created|updated",
  "object_id": 123,
  "object_data": { ... payload NetBox ... },
  "dry_run": false
}
```

---

## Diagrama de fluxo

```
[Trigger: Workflow input]
    ↓
[HTTP: GET NetBox device full] (com depth=2 para trazer site, role, platform, tenant)
    ↓
[Code: Validate device meets criteria]
    │
    ├── monitoring_enabled=false → [Branch: ensure_disabled] ──→ END
    │
    └── monitoring_enabled=true → continua
    ↓
[Code: Resolve desired state]
    (usa role_template_map.yaml + criticality_profiles.yaml)
    ↓
[HTTP: Zabbix host.get by host=device.name]
    │
    ├── existe → [Code: Compute diff] ──→ [Switch: diff?]
    │                                         ├── empty   → [audit "noop"] → END
    │                                         └── changed → [HTTP: host.update]
    │
    └── não existe → [HTTP: ensure host_groups exist]
                       ↓
                     [HTTP: host.create]
    ↓
[HTTP: Apply tags] (host.update with tags)
    ↓
[HTTP: Apply macros] (host.massupdate with macros)
    ↓
[Postgres: audit "created|updated|noop"]
    ↓
[IF: Notify NOC?] (somente se created ou error)
    ↓
[HTTP: Evolution API send message]
    ↓
END
```

---

## Nodes — detalhe

### 1. Trigger: Workflow input
Receives input from router.

### 2. HTTP: GET NetBox device
**Method:** GET
**URL:** `{{ $env.NETBOX_URL }}/api/dcim/devices/{{ $json.object_id }}/?include=custom_fields&brief=false`
**Authentication:** netbox-api credential
**Options:** Timeout 10000ms, Retry on Fail 3x

Output esperado: JSON completo do device com `site`, `role`, `device_type.manufacturer`, `platform`, `tenant`, `custom_fields`, `primary_ip4`.

### 3. Code: Validate
**Code:**
```javascript
const dev = $input.first().json;

const errors = [];

if (!dev.custom_fields?.monitoring_enabled) {
    return [{ json: { skip: true, reason: 'monitoring_disabled', device: dev } }];
}

if (!dev.custom_fields?.criticality) {
    errors.push('missing criticality');
}
if (!dev.custom_fields?.device_purpose) {
    errors.push('missing device_purpose');
}
if (!dev.platform?.manufacturer?.slug) {
    errors.push('missing platform.manufacturer.slug');
}
if (!dev.site?.slug) {
    errors.push('missing site.slug');
}
if (!dev.primary_ip4) {
    errors.push('missing primary_ip4');
}

if (errors.length > 0) {
    throw new Error(`Validation failed: ${errors.join(', ')} for device id=${dev.id} name=${dev.name}`);
}

return [{ json: { skip: false, device: dev } }];
```

### 4. IF: skip?
- skip=true → [Branch: ensure_disabled] (vide nó 14)
- skip=false → continua

### 5. Code: Resolve desired state
**Carrega config files do Git** (HTTP GET ao raw GitLab/GitHub):

```javascript
// Carregar configs (em produção, cachear via Redis)
const yaml = require('js-yaml');

// Estes URLs apontam para raw files do monorepo
const ROLE_MAP_URL = $env.ROLE_TEMPLATE_MAP_URL;
const CRIT_PROFILES_URL = $env.CRITICALITY_PROFILES_URL;

// Em N8N, fazer HTTP nodes separados antes deste Code para puxar.
// Aqui assumimos que vieram em $items[0..2]
const roleMap = $('HTTP: Get role_template_map').item.json;       // já parseado
const critProfiles = $('HTTP: Get criticality_profiles').item.json;

const dev = $('Code: Validate').item.json.device;

const role = dev.custom_fields.device_purpose;     // ex: 'pe'
const vendor = dev.platform.manufacturer.slug;      // ex: 'huawei'
const tenantSlug = dev.tenant?.slug || 'k3g';
const popSlug = dev.site.slug;
const criticality = dev.custom_fields.criticality;  // ex: 'gold'

const roleConfig = roleMap.roles[role];
if (!roleConfig) throw new Error(`Unknown role: ${role}`);

const baseTemplate = roleConfig.base_by_vendor[vendor];
if (!baseTemplate) throw new Error(`Unknown vendor ${vendor} for role ${role}`);

const templates = [
    baseTemplate,
    roleConfig.role,
    ...(roleConfig.services || []),
    ...(roleMap.universal || [])
];

// Host groups hierárquicos
const groups = roleMap.host_groups_pattern.map(p =>
    p.replace('{environment}', $env.ENVIRONMENT || 'prod')
     .replace('{site_slug}', popSlug)
     .replace('{device_purpose}', role)
     .replace('{tenant_slug}', tenantSlug)
     .replace('{vendor_slug}', vendor)
);

// Tags base
const tags = [
    { tag: 'environment',  value: $env.ENVIRONMENT || 'prod' },
    { tag: 'tenant',       value: tenantSlug },
    { tag: 'pop',          value: popSlug },
    { tag: 'device_role',  value: role },
    { tag: 'vendor',       value: vendor },
    { tag: 'criticality',  value: criticality },
    { tag: 'netbox_id',    value: String(dev.id) }
];

// Macros derivadas de criticality
const profile = critProfiles.profiles[criticality];
if (!profile) throw new Error(`Unknown criticality: ${criticality}`);

const macros = [
    { macro: '{$POLL.INTERVAL}',   value: profile.poll_interval },
    { macro: '{$ALERT.PROFILE}',   value: criticality },
    { macro: '{$SLA.TARGET}',      value: String(profile.sla_target_pct) },
    // SNMP credentials vêm de N8N credentials, não hardcoded
    { macro: '{$SNMP.COMMUNITY}',  value: $env.SNMP_COMMUNITY_RO, type: 1 }
];

return [{
    json: {
        device_name: dev.name,
        device_id: dev.id,
        ip: dev.primary_ip4.address.split('/')[0],
        templates,
        groups,
        tags,
        macros,
        // Para auditoria/notificação
        tenant_name: dev.tenant?.name || 'k3g',
        site_name: dev.site.name,
        criticality
    }
}];
```

### 6. HTTP: Zabbix host.get
**Method:** POST
**URL:** `{{ $env.ZABBIX_URL }}`
**Body (JSON):**
```json
{
  "jsonrpc": "2.0",
  "method": "host.get",
  "params": {
    "filter": { "host": ["{{ $json.device_name }}"] },
    "selectInterfaces": ["interfaceid","ip","type"],
    "selectParentTemplates": ["templateid","name"],
    "selectGroups": ["groupid","name"],
    "selectTags": ["tag","value"],
    "selectMacros": ["macro","value"]
  },
  "id": 1
}
```
Auth: zabbix-api credential.

### 7. Code: Compute diff
```javascript
const desired = $('Code: Resolve desired state').item.json;
const current = $input.first().json.result;

if (current.length === 0) {
    return [{ json: { action: 'create', desired, current: null } }];
}

const host = current[0];

// Compare templates (set de templateids)
const currentTpl = new Set(host.parentTemplates.map(t => t.name));
const desiredTpl = new Set(desired.templates);
const tplChanged = currentTpl.size !== desiredTpl.size ||
    [...desiredTpl].some(t => !currentTpl.has(t));

// Compare groups (set de nomes)
const currentGrp = new Set(host.groups.map(g => g.name));
const desiredGrp = new Set(desired.groups);
const grpChanged = currentGrp.size !== desiredGrp.size ||
    [...desiredGrp].some(g => !currentGrp.has(g));

// Compare tags (chave-valor)
const currentTags = new Map(host.tags.map(t => [t.tag, t.value]));
const tagsChanged = desired.tags.some(t => currentTags.get(t.tag) !== t.value);

// Compare macros
const currentMacros = new Map(host.macros.map(m => [m.macro, m.value]));
const macrosChanged = desired.macros.some(m => currentMacros.get(m.macro) !== m.value);

const anyChange = tplChanged || grpChanged || tagsChanged || macrosChanged;

return [{
    json: {
        action: anyChange ? 'update' : 'noop',
        hostid: host.hostid,
        desired,
        diff: {
            templates: tplChanged,
            groups: grpChanged,
            tags: tagsChanged,
            macros: macrosChanged
        }
    }
}];
```

### 8. Switch: action
- `action == 'noop'` → [Postgres: audit noop] → END
- `action == 'create'` → continua para 9-10
- `action == 'update'` → continua para 11-13

### 9. (CREATE branch) Code: Ensure host_groups
Para cada grupo em `desired.groups`, garante que existe (cria se não):

```javascript
// Pseudocódigo — em N8N, fazer um loop com Split In Batches
const desired = $input.first().json.desired;
const items = desired.groups.map(name => ({ json: { name } }));
return items;
```

Depois SplitInBatches → HTTP node:
**hostgroup.get** filtrando `name`. Se vazio, **hostgroup.create**.
Coletar `groupid`s.

### 10. (CREATE branch) HTTP: host.create
```json
{
  "jsonrpc": "2.0",
  "method": "host.create",
  "params": {
    "host": "={{ $json.desired.device_name }}",
    "interfaces": [{
      "type": 2, "main": 1, "useip": 1,
      "ip": "={{ $json.desired.ip }}",
      "dns": "", "port": "161",
      "details": {
        "version": 3, "bulk": 1,
        "securityname": "{$SNMP.V3.SECURITYNAME}",
        "securitylevel": 2,
        "authprotocol": 6, "authpassphrase": "{$SNMP.V3.AUTHPASSPHRASE}",
        "privprotocol": 8, "privpassphrase": "{$SNMP.V3.PRIVPASSPHRASE}",
        "contextname": ""
      }
    }],
    "groups": "={{ $json.group_ids }}",
    "templates": "={{ $json.template_ids }}",
    "tags": "={{ $json.desired.tags }}",
    "macros": "={{ $json.desired.macros }}"
  },
  "id": 2
}
```

### 11. (UPDATE branch) HTTP: hostgroup.get / create se necessário
Mesmo loop do passo 9.

### 12. (UPDATE branch) HTTP: template.get para resolver IDs
```json
{
  "jsonrpc": "2.0",
  "method": "template.get",
  "params": {
    "filter": { "host": "={{ $json.desired.templates }}" },
    "output": ["templateid","name"]
  },
  "id": 3
}
```

### 13. (UPDATE branch) HTTP: host.update
```json
{
  "jsonrpc": "2.0",
  "method": "host.update",
  "params": {
    "hostid": "={{ $json.hostid }}",
    "groups": "={{ $json.group_ids }}",
    "templates_clear": [],
    "templates": "={{ $json.template_ids }}",
    "tags": "={{ $json.desired.tags }}",
    "macros": "={{ $json.desired.macros }}"
  },
  "id": 4
}
```

> **Atenção:** `templates_clear` vazio NÃO desliga templates antigos. Se o role mudou e templates antigos sobram, eles permanecem. Para "templates_clear", preciso enviar a lista do que sair. Isso é uma sutileza importante:
> ```javascript
> // No Code: Compute diff, calcular também:
> const templates_to_remove = [...currentTpl].filter(t => !desiredTpl.has(t));
> ```

### 14. (DISABLE branch) HTTP: host.update status=1
Quando `monitoring_enabled=false`:
```json
{
  "jsonrpc": "2.0",
  "method": "host.update",
  "params": {
    "hostid": "={{ $json.hostid }}",
    "status": 1,
    "groups": [{"groupid":"<id de /Decommissioned>"}]
  },
  "id": 5
}
```
**Não deletar.** Preserva histórico SLA.

### 15. Postgres: audit
```sql
INSERT INTO monitoring_audit_log
    (workflow, action, object_type, netbox_id, zabbix_id, diff,
     dry_run, trigger_source, correlation_id, actor)
VALUES
    ('wf-onboard-device', $1, 'device', $2, $3, $4, $5, 'webhook', $6, 'n8n');
```

### 16. IF: Notify?
Notificar Evolution API se:
- `action == 'created'` (cliente novo, NOC quer saber)
- `action == 'error'` (sempre)
- `criticality IN ('platinum','gold')` (mesmo update gera notificação)

### 17. HTTP: Evolution API
```json
POST {{$env.EVOLUTION_API_URL}}/message/sendText/{{$env.EVOLUTION_INSTANCE_NOC}}
{
  "number": "{{$env.NOC_GROUP_CHATID}}",
  "text": "🆕 Device monitorado\n*{{ $json.device_name }}*\nPOP: {{ $json.site_name }}\nTenant: {{ $json.tenant_name }}\nRole: {{ $json.device_role }}\nCriticality: {{ $json.criticality }}\nAção: {{ $json.action }}"
}
```

### 18. Error Trigger → wf-error-handler

---

## Dry-run mode

Quando `dry_run=true`, todos os nodes HTTP de **escrita** (host.create, host.update, hostgroup.create) são pulados via IF antes deles. Audit grava com `dry_run=true`.

Workflow ainda executa GET, valida, computa diff, mas não aplica.

Como saber o que ele faria? Audit com `action='created'` + `dry_run=true` significa "teria criado se não fosse dry-run".

---

## Smoke test

### A. Device sem `monitoring_enabled`
1. NetBox: device com `monitoring_enabled=false`.
2. Trigger via webhook (ou Test Workflow no N8N).
3. **Esperado:** audit `action=skipped`, reason=`monitoring_disabled`. Nenhuma chamada Zabbix.

### B. Device novo, válido
1. NetBox: device com `monitoring_enabled=true`, `criticality=gold`, `device_purpose=pe`, vendor=huawei.
2. Trigger.
3. **Esperado:**
   - Audit `action=created`.
   - Host existe no Zabbix com nome correto, IP, SNMP v3.
   - Host groups: `/Environments/prod`, `/POPs/<site>`, `/Roles/pe`, `/Tenants/<tenant>`, `/Vendors/huawei`.
   - Templates linkados: `T_HUAWEI_NE8000_BASE`, `T_ROLE_PE`, `T_SVC_BGP_PEERING`, `T_SVC_L2VPN_VPWS`, `T_SVC_L3VPN_VRF`, `T_SVC_INTERFACE_CUSTOMER`, `T_SVC_INTERFACE_CARRIER`, `T_SVC_OPTICAL_SFP`, `T_GOV_NAMING_COMPLIANCE`, `T_GOV_HEARTBEAT_AGENT`, `T_GOV_NETBOX_SYNC_HEALTH`.
   - Tags: 7 tags base.
   - Macros: `{$POLL.INTERVAL}=60s`, `{$ALERT.PROFILE}=gold`, etc.

### C. Re-rodar mesmo evento
1. Disparar mesmo webhook 5x consecutivo.
2. **Esperado:** 1ª vez `action=created`. Demais: `action=noop`. (idempotência)

### D. Mudança de criticality
1. NetBox: alterar device de `criticality=gold` para `platinum`.
2. **Esperado:** audit `action=updated`, diff mostra `tags=true, macros=true`. Macro `{$POLL.INTERVAL}` atualizada para `30s`.

### E. Decommission
1. NetBox: `monitoring_enabled` true → false.
2. **Esperado:** audit `action=disabled`. Host status=1 no Zabbix, movido para `/Decommissioned`. Histórico preservado.

### F. Validation failure
1. NetBox: device sem `criticality`.
2. **Esperado:** Workflow falha. Error trigger dispara `wf-error-handler`. Audit `action=error` com `error_msg`. WhatsApp NOC alertado.

---

## Latência esperada

- p50: 2-4s (3 GETs Zabbix + 1 GET NetBox + 1 host.update)
- p95: < 8s
- p99: < 15s

Acima disso, investigar Zabbix API performance.
