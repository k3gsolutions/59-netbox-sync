# Report History Standard — Compliance v1.1

## Objetivo

Manter histórico local de relatórios Markdown de compliance por device, permitindo comparação de execuções sem exposição de secrets.

## Estrutura de diretórios

```
reports/pilot-device-compliance/
├── current/
│   ├── DEVICE-A-compliance-report.md
│   ├── DEVICE-B-compliance-report.md
│   └── ...
├── history/
│   ├── DEVICE-A/
│   │   ├── 2026-04-28T10:30:45Z-compliance-report.md
│   │   ├── 2026-04-28T14:15:30Z-compliance-report.md
│   │   └── ...
│   ├── DEVICE-B/
│   │   ├── 2026-04-28T09:00:00Z-compliance-report.md
│   │   └── ...
│   └── ...
├── comparisons/
│   ├── 2026-04-28-comparison.md
│   ├── DEVICE-A-2026-04-27--2026-04-28-comparison.md
│   └── ...
├── index.json
└── README.md
```

## Naming Convention

**Current reports:**
```
{DEVICE-NAME}-compliance-report.md
```
- `{DEVICE-NAME}`: device name cadastrado no NetBox (ex: `4WNET-MNS-KTG-RX`)
- Filename: lowercase, hífens para separador

**Historical reports:**
```
history/{DEVICE-NAME}/{ISO8601-TIMESTAMP}-compliance-report.md
```
- `{ISO8601-TIMESTAMP}`: UTC, format `2026-04-28T10:30:45Z`
- Each device has own subdirectory in history/

## Index.json Format

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
    },
    "ROUTER-B": {
      "device_id": 1891,
      "last_report": "2026-04-28T13:00:00Z",
      "reports_count": 5,
      "history_path": "history/ROUTER-B"
    }
  },
  "retention_policy": {
    "keep_days": 90,
    "keep_count_per_device": null,
    "enabled": true
  }
}
```

## Regras de Retenção

- Manter últimos 90 dias de histórico (configurável em index.json)
- Sem limite de relatórios por device (remover apenas por data)
- Executar cleanup periodicamente via script ou CI

## O que CAN ser versionado

✅ **Markdown relatórios** (.md) — sem secrets
✅ **index.json** — histórico estruturado
✅ **docs/20-report-history-standard.md** — este padrão
✅ **.gitignore** — excluda raw JSON sensível

## O que NÃO pode ser versionado

❌ **payload.local.json** — contém credenciais SSH/NetBox
❌ **\*raw\*.json** — JSON bruto com parâmetros
❌ **\*secret\*.json** — qualquer arquivo com secrets
❌ **reports/pilot-device-compliance/payload.\*** — ignora

## .gitignore para reports/

```
# Raw payloads with credentials
payload*.json
*raw*.json
*secret*.json

# Python cache
__pycache__/
*.pyc
.pytest_cache/

# Local-only archives (restore from history if needed)
# Keep only current/ and history/ .md files
```

## Comparar Execuções

Usar script local:
```bash
python3 tools/local/compare_compliance_reports.py \
  --device 4WNET-MNS-KTG-RX \
  --report1 history/4WNET-MNS-KTG-RX/2026-04-28T10:00:00Z-compliance-report.md \
  --report2 reports/pilot-device-compliance/current/4WNET-MNS-KTG-RX-compliance-report.md
```

Output: divergências novas/resolvidas, warnings mudanças, ações recomendadas delta.

## Preparar Web UI (futuro)

Dados necessários para UI:
1. `index.json` — lista devices e timestamps
2. `history/{DEVICE-NAME}/*.md` — arquivo de cada execução
3. Diff entre execuções (via script compare_compliance_reports.py)

Web UI pode:
- Listar devices com último relatório
- Timeline de execuções por device
- Diff visual entre execuções
- Filtrar por date range, severity, código divergência
- Exportar histórico em CSV/PDF

## Tooling Local

Scripts em `tools/local/`:
- `archive_compliance_report.py` — arquivar relatório novo
- `compare_compliance_reports.py` — comparar dois relatórios
- `cleanup_compliance_history.py` — remover relatórios antigos
- `export_compliance_csv.py` — exportar histórico em CSV

Todos usam standard library Python, sem dependências externas.
