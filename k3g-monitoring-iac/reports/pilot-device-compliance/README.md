# Compliance Reports — Pilot Device

Histórico local de relatórios Markdown de compliance por device, sem exposição de secrets.

## Estrutura

- **current/** — último relatório de cada device
- **history/** — histórico completo com timestamps
- **comparisons/** — comparativos entre execuções
- **index.json** — metadados (device_id, contagem, último timestamp)

## Arquivo Relatório

Usar script local:

```bash
python3 tools/local/archive_compliance_report.py \
  --report reports/pilot-device-compliance/pilot-device-compliance-report.md \
  --device 4WNET-MNS-KTG-RX \
  --device-id 1890
```

Script:
- Lê relatório .md
- Copia para `history/{DEVICE}/{timestamp}-compliance-report.md`
- Atualiza `current/{DEVICE}-compliance-report.md`
- Incrementa contador em `index.json`

## ImportPlan

A partir da fase atual, o fluxo de compliance também gera um ImportPlan read-only para validar propostas de enriquecimento do NetBox.

- Endpoints implementados: `/compliance/import-plan` e `/compliance/import-plan/report`
- Classificação: `safe_create_staged`, `needs_review`, `blocked`, `ignore`
- Naming inválido nunca vira `safe_create_staged`
- Nunca gera `delete`
- Sem escrita no NetBox
- Sem `/sync`
- Sem alteração em equipamento
- ImportPlan real gerado para `4WNET-MNS-KTG-RX`
- FASE 2.0 completed: first real staged apply for Eth-Trunk0 with 201 Created and post-apply compliance validated
- Recommended next: FASE 2.2 — política para múltiplos staged applies em lote controlado, ainda limitado a base_inventory

## Comparar Relatórios

Usar script local:

```bash
python3 tools/local/compare_compliance_reports.py \
  --old history/4WNET-MNS-KTG-RX/2026-04-28T05:53:00Z-compliance-report.md \
  --new current/4WNET-MNS-KTG-RX-compliance-report.md \
  --output comparisons/2026-04-28-comparison.md \
  --device 4WNET-MNS-KTG-RX
```

Script gera:
- Tabela: evolução por severidade (antes/agora/delta)
- Tabela: novas divergências
- Tabela: divergências resolvidas
- Tabela: divergências recorrentes (ainda pendentes)
- Sem API real, sem secrets

## O que é versionado?

✅ `current/*.md` — último relatório (sem secrets)
✅ `history/**/*.md` — histórico (sem secrets)
✅ `index.json` — metadados estruturados
✅ `.gitignore` — exclui raw JSON

❌ `*.local.json` — payload com credenciais
❌ `*raw*.json` — JSON bruto
❌ `*secret*.json` — qualquer secret

## Documentação Completa

Ver `docs/20-report-history-standard.md` para:
- Naming convention detalhado
- Formato index.json completo
- Regras de retenção
- Como comparar execuções
- Preparação para Web UI

## Exemplo index.json

```json
{
  "version": "1.1",
  "generated_at": "2026-04-28T14:30:00Z",
  "devices": {
    "4WNET-MNS-KTG-RX": {
      "device_id": 1890,
      "last_report": "2026-04-28T14:25:00Z",
      "reports_count": 12,
      "history_path": "history/4WNET-MNS-KTG-RX"
    }
  },
  "retention_policy": {
    "keep_days": 90,
    "keep_count_per_device": null,
    "enabled": true
  }
}
```
