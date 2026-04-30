# Web UI Operator Experience Polish — FASE 4.69

## Objetivo
Melhorar clareza da Web UI para operador entender status de ciclos, warnings e próximos passos.

## Mudanças de UI

### 1. Página de Ciclos (`/controlled-operation/cycles`)

**Antes:**
```
Cycle-002 | CLOSED_WITH_WARNINGS | 2026-04-30
Cycle-003 | PLANNED_NOT_STARTED | 2026-05-01
```

**Depois:**
```
Cycle-002
├─ Status: ✓ Concluído com Restrições
├─ Escrita: IP 203.0.113.1/32 (NetBox ID 6324)
├─ Warnings: Drift de enum/formatação (não-bloqueante)
└─ Expansion: STAY_CURRENT_LEVEL mantido

Cycle-003
├─ Status: ⏳ Planejado — Aguardando Start Gate
├─ Limites: 1 device, 3 items, POST-only
├─ Restrictions: Herdadas do Cycle-002
└─ Próximo: Week 1 Intake
```

### 2. Detalhe de Ciclo (`/controlled-operation/cycle-002`)

**Card Principal:**
```
Cycle-002 — 4WNET-MNS-KTG-RX
├─ Objeto Criado: IP 203.0.113.1/32 (NetBox ID 6324)
├─ Status Execução: ✓ CYCLE_REAL_WRITE_SUCCESS
├─ Status Closure: ⚠️ CYCLE_CLOSED_WITH_WARNINGS
└─ Decisão Handoff: CYCLE_CLOSED_WITH_RESTRICTIONS
```

**Seção de Warnings:**
```
⚠️ Warnings Controlados (Não-bloqueantes)
- Post-Write Verification: PASSED_WITH_DRIFT
  └─ Motivo: Formatação de enum (status: "active" vs {"value":"active","label":"Active"})
- Compliance: PASSED_WITH_WARNINGS
  └─ Motivo: Drift format detectado, sem impacto operacional
```

**Badges:**
- ✓ Sucesso
- ⚠️ Com Restrições
- ❌ Ação Necessária
- ⏳ Planejado
- 🚫 Bloqueado

### 3. Página de Handoff (`/controlled-operation/cycle-002/handoff`)

```
Decisão: CYCLE_CLOSED_WITH_RESTRICTIONS

Evidências:
├─ Execução: CYCLE_REAL_WRITE_SUCCESS ✓
├─ Verificação: CYCLE_POST_WRITE_VERIFICATION_PASSED_WITH_DRIFT ⚠️
├─ Compliance: CYCLE_POST_WRITE_COMPLIANCE_PASSED_WITH_WARNINGS ⚠️
├─ Closure: CYCLE_CLOSED_WITH_WARNINGS ⚠️
└─ Archive: CYCLE_ARCHIVED_SUCCESS ✓

Restrições para Próximo Ciclo:
- Manter max_items=3
- Manter allowed_methods=[POST]
- Manter STAY_CURRENT_LEVEL de expansão
- Normalizar validadores para enum/format
```

### 4. Página de Cycle-003 (`/controlled-operation/cycle-003`)

```
Cycle-003 — 4WNET-MNS-KTG-RX — STATUS: PLANEJADO

Escopo:
├─ Max Devices: 1
├─ Max Items: 3
├─ Métodos Permitidos: POST
└─ Targets Bloqueados: /sync, equipment, ssh, netconf

Próximas Etapas:
1. ⏳ Start Gate (configurado)
2. ⏳ Week 1 Intake
3. ⏳ Week 1 Validation
4. → Week 2 Review
5. → Approvals
6. → ApplyPlan Dry-Run
7. → Real Write

[INICIAR CYCLE-003] (quando start gate OK)
```

## O Que NÃO Mostrar

- ❌ Token NETBOX_WRITE_TOKEN
- ❌ Authorization header
- ❌ Botão "Apply ApplyPlan"
- ❌ Botão "Executar Sync"
- ❌ Botão "Retry Automático"
- ❌ Botão "Rollback"
- ❌ Botão "Escrita Direta"
- ❌ Payload raw JSON (com values numéricos altos)
- ❌ Log do token ou credencial

## Cores e Ícones

```
Status Sucesso        → Verde (✓)
Status Warning        → Amarelo (⚠️)
Status Bloqueado      → Vermelho (❌)
Status Planejado      → Azul (⏳)
Status Ação Req.      → Laranja (⚡)
Drift Não-bloqueante  → Cinza (ℹ️)
```

## Implementação

**Arquivo:** `webui/app.py`

```python
@app.route("/controlled-operation/cycle-002")
def view_cycle_002():
    cycle = load_cycle_002_data()
    return render_template(
        "controlled_operation_cycle_detail.html",
        cycle=cycle,
        status="CLOSED_WITH_RESTRICTIONS",
        badges=["success", "with_restrictions"],
        object_created="203.0.113.1/32",
        netbox_id=6324,
        warnings=[
            {
                "type": "drift_format",
                "level": "non_blocking",
                "message": "Enum formatting difference (no operational impact)"
            }
        ]
    )
```

## Template

**Arquivo:** `webui/templates/controlled_operation_cycle_detail.html`

```html
<div class="cycle-card">
  <h2>{{ cycle.cycle_id }}</h2>
  <div class="badges">
    {% for badge in cycle.badges %}
      <span class="badge badge-{{ badge }}">{{ badge_label(badge) }}</span>
    {% endfor %}
  </div>

  <div class="object-created">
    <strong>Objeto Criado:</strong> {{ cycle.object_created }}
    (NetBox ID: {{ cycle.netbox_id }})
  </div>

  <div class="warnings">
    {% for warning in cycle.warnings %}
      <div class="warning warning-{{ warning.level }}">
        {{ warning.message }}
      </div>
    {% endfor %}
  </div>
</div>
```

## Testes

Verificar:
- [ ] Cycle-002 mostra "Concluído com Restrições"
- [ ] IP criado exibido: 203.0.113.1/32
- [ ] NetBox ID 6324 visível
- [ ] Warning de drift não-bloqueante exibido
- [ ] Expansion STAY_CURRENT_LEVEL mostrado
- [ ] Nenhum token visível
- [ ] Nenhum botão POST/PATCH/DELETE/sync/retry/rollback
- [ ] Cycle-003 mostra "Planejado"
- [ ] Restrições documentadas
- [ ] Start gate link funciona

## Satisfação do Operador

Operador deve ser capaz de:
1. ✓ Entender que Cycle-002 foi bem-sucedido
2. ✓ Saber qual objeto foi criado
3. ✓ Entender que warnings são format-only
4. ✓ Ver que limites foram mantidos
5. ✓ Saber quando iniciar Cycle-003
6. ✓ Usar UI sem expor credenciais

---
FASE 4.69 complete — UI polished for operator clarity
