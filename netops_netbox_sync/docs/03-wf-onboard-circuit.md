# wf-onboard-circuit

Provisiona itens Zabbix relacionados a um circuito (L2VPN/L3VPN/Internet) — aplicado nos hosts PE que terminam o circuito.

**Acionado por:** `wf-netbox-router` quando `model=circuits.circuit`.

**Sprint 1 status:** opcional. Implementar se já tiver hosts PE provisionados via `wf-onboard-device`. Caso contrário, deixar para Sprint 2.

**Princípio:** circuito não vira host Zabbix — vira **tags + macros nos hosts PE existentes** + LLD descobre interfaces que casem o naming convention.

---

## Como circuit vira monitoramento

Um `Circuit` no NetBox tem 2 `CircuitTermination` (lado A e B). Cada termination está em uma `Site` e tem `cabling` que conecta a uma `Interface` em um `Device`.

Quando webhook chega:
1. Pega circuit com terminations.
2. Resolve hosts PE (via terminations → cable → interface → device).
3. Para cada PE: aplica tags `circuit_id`, `service_type`, `tenant`, `criticality` no nível **host** (ou cria macro `{$CIRCUIT.<id>}`).
4. Garante que descrição da interface no equipamento casa o naming convention (linter — opcional Sprint 1).
5. LLD do template `T_SVC_INTERFACE_CUSTOMER` (já no host) descobre a interface, parseia ifAlias, aplica tags no nível **item**.

> **Importante:** o sync **não escreve** no equipamento neste sprint. Se a interface não tem descrição correta, o LLD marca `compliant=false` e abre alerta de governança. Operador humano corrige a descrição via fluxo de change normal.

---

## Diagrama

```
[Trigger: workflow input]
    ↓
[HTTP: GET NetBox circuit + terminations]
    ↓
[Code: Validate (monitoring_enabled, both terminations cabled)]
    ↓
[HTTP: GET interfaces das terminations] (lookup via cable)
    ↓
[Code: Build per-PE tag set]
    ↓
[Loop por PE]
    ├── [HTTP: Zabbix host.get pelo nome do device PE]
    │       │
    │       ├── não existe → [audit "skipped: pe_not_provisioned"]
    │       │                + alerta WhatsApp engenharia
    │       │
    │       └── existe → [HTTP: host.update com circuit tags]
    │                  → [audit "updated"]
    ↓
END
```

---

## Nodes — detalhe

### 1. Trigger
Input: `{ correlation_id, event, object_id, dry_run }`.

### 2. HTTP: GET NetBox circuit
**URL:** `{{$env.NETBOX_URL}}/api/circuits/circuits/{{$json.object_id}}/?include=terminations,custom_fields`

### 3. HTTP: GET NetBox circuit terminations
**URL:** `{{$env.NETBOX_URL}}/api/circuits/circuit-terminations/?circuit_id={{$json.id}}`

### 4. Code: Validate
```javascript
const circuit = $('HTTP: GET NetBox circuit').item.json;
const terms = $('HTTP: GET NetBox circuit terminations').item.json.results;

if (!circuit.custom_fields?.monitoring_enabled) {
    return [{ json: { skip: true, reason: 'monitoring_disabled' } }];
}
if (!circuit.custom_fields?.service_type) {
    throw new Error(`Circuit ${circuit.cid} missing service_type`);
}
if (!circuit.custom_fields?.criticality) {
    throw new Error(`Circuit ${circuit.cid} missing criticality`);
}
if (terms.length < 1) {
    throw new Error(`Circuit ${circuit.cid} has no terminations`);
}

// Para circuitos que terminam em equipamento próprio (lado A=customer-internet)
// pode ter apenas 1 termination "interna". Para L2VPN VPWS, esperamos 2.
return [{
    json: {
        skip: false,
        circuit,
        terminations: terms,
        tenant_slug: circuit.tenant?.slug || 'unknown',
        service_type: circuit.custom_fields.service_type,
        criticality: circuit.custom_fields.criticality,
        bandwidth_mbps: circuit.custom_fields.bandwidth_mbps || null,
        vc_id: circuit.custom_fields.vc_id || null
    }
}];
```

### 5. Code: Resolve PE hosts from terminations
```javascript
// Para cada termination, descobrir o device através do cable
const terms = $('Code: Validate').item.json.terminations;
const peHosts = [];

for (const term of terms) {
    if (!term.cable) continue;   // termination não cabeada (lado operadora externa)

    // Buscar cable detalhes
    // (em N8N, fazer um node HTTP separado para cada cable_id)
    // Simplificação aqui — assume que cable já vem expandido
    const interfaceObj = term.cable.terminations?.find(t => t.object_type === 'dcim.interface')?.object;
    if (!interfaceObj) continue;

    peHosts.push({
        device_name: interfaceObj.device.name,
        interface_name: interfaceObj.name,
        site_slug: interfaceObj.device.site.slug,
        side: term.term_side    // 'A' ou 'Z'
    });
}

if (peHosts.length === 0) {
    return [{ json: { skip: true, reason: 'no_internal_terminations' } }];
}

return peHosts.map(pe => ({ json: pe }));
```

> **Observação:** o resolve real exige 1+ chamadas extras a `/api/dcim/cables/{id}/` para cada termination. Em N8N, encadear via `HTTP Request` em loop ou usar GraphQL endpoint do NetBox para single round-trip.

### 6. Loop: para cada PE
**Node:** Split In Batches (size=1)

### 7. HTTP: Zabbix host.get
```json
{
  "jsonrpc": "2.0",
  "method": "host.get",
  "params": {
    "filter": { "host": ["{{ $json.device_name }}"] },
    "selectMacros": ["macro","value"],
    "selectTags": ["tag","value"],
    "output": ["hostid","host"]
  },
  "id": 1
}
```

### 8. IF: host exists?
- **Não existe:** audit `skipped` + Evolution API alerta engenharia ("circuit X provisionado mas PE Y não está em monitoramento — provisione device primeiro"). **Não falha.**
- **Existe:** continua.

### 9. Code: Compute new macros
Cada circuito vira **uma macro com prefixo** no host PE, para troubleshoot rápido:

```javascript
const circuit = $('Code: Validate').item.json.circuit;
const pe = $('Loop').item.json;
const validate = $('Code: Validate').item.json;

const cid = circuit.cid;          // ex: "L2VPN-2017"
const macroKey = `{$CIRCUIT.${circuit.id}}`;
const macroValue = JSON.stringify({
    cid,
    service_type: validate.service_type,
    tenant: validate.tenant_slug,
    criticality: validate.criticality,
    interface: pe.interface_name,
    side: pe.side,
    bandwidth_mbps: validate.bandwidth_mbps,
    vc_id: validate.vc_id
});

return [{ json: { hostid: $('HTTP: Zabbix host.get').item.json.result[0].hostid,
                  macro: macroKey, value: macroValue } }];
```

### 10. HTTP: Zabbix usermacro.create (ou update se existir)
```json
{
  "jsonrpc": "2.0",
  "method": "usermacro.create",
  "params": {
    "hostid": "={{ $json.hostid }}",
    "macro": "={{ $json.macro }}",
    "value": "={{ $json.value }}"
  },
  "id": 2
}
```

> Em caso de erro "macro already exists", chamar `usermacro.update`. Idempotência exige.

### 11. Postgres: audit
```sql
INSERT INTO monitoring_audit_log (...) VALUES (
  'wf-onboard-circuit', 'updated', 'circuit', $1, $2, ...);
```

### 12. Error Trigger → wf-error-handler

---

## O que **não** faz neste workflow (importante)

❌ Cria item Zabbix manualmente para o circuito.
- Por quê: LLD do template `T_SVC_INTERFACE_CUSTOMER` no host PE descobre automaticamente. Criar manual = drift.

❌ Aplica descrição na interface do equipamento.
- Por quê: equipamento é read-only nesta plataforma. Linter externo (Sprint 2) sugere descrição; operador aplica via fluxo de change.

❌ Cria dashboard Grafana específica para o circuit.
- Por quê: dashboard `customer-circuit-detail.json` é genérica, filtrada por `circuit_id` (Sprint 3).

---

## Smoke test

### A. Circuit novo L2VPN VPWS, ambos PEs já provisionados
1. NetBox: criar circuit `service_type=customer-l2vpn`, `criticality=gold`, terminations cabeados em 2 interfaces de PEs.
2. **Esperado:**
   - Audit em 2 PEs (lado A e lado Z), `action=updated`.
   - Cada PE recebe macro `{$CIRCUIT.<id>}` com JSON do circuit.
   - Nenhum host novo criado.

### B. Circuit, mas PE não está provisionado
1. NetBox: circuit terminado em device com `monitoring_enabled=false`.
2. **Esperado:**
   - Audit `action=skipped`, reason `pe_not_provisioned`.
   - WhatsApp engenharia alerta.

### C. Update circuit (criticality bronze → gold)
1. NetBox: alterar `criticality` do circuit.
2. **Esperado:**
   - Audit `action=updated`.
   - Macro `{$CIRCUIT.<id>}` atualizada com novo criticality.
   - **Atenção:** triggers do template não atualizam severidade automaticamente — isso vem da tag do **item** que é descoberto pelo LLD. Esperar próximo ciclo LLD (1h por padrão) ou forçar.

### D. Circuit deletado
1. NetBox: deletar circuit.
2. Webhook `event=deleted`, model `circuits.circuit`.
3. (Sprint 2) wf-decommission-circuit: remove macro `{$CIRCUIT.<id>}` dos PEs envolvidos.

---

## Latência

- p50: 3-5s (envolve múltiplos GETs NetBox + 2 PE updates).
- p95: < 10s.

Para circuitos VPLS multi-site (>2 terminations), latência cresce linearmente.
