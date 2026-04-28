# Compliance History Maintenance — v1.0

Limpeza, retenção e exportação do histórico de relatórios.

## Limpeza — Cleanup

Remover relatórios antigos baseado em política de retenção.

### Dry-run (padrão — não deleta)

```bash
python3 tools/local/cleanup_compliance_history.py \
  --keep-days 90 \
  [--keep-count 100]
```

**Output:**
- Lista de relatórios que seriam deletados
- Contagem por device
- Timestamps dos reports

### Apply (deletar efetivamente)

```bash
python3 tools/local/cleanup_compliance_history.py \
  --keep-days 90 \
  --apply
```

**Ações:**
- Deleta relatórios older than N days
- Atualiza `reports_count` em `index.json`
- Mantém `current/`, `comparisons/`, `index.json` intactos

### Política de retenção

Default:
- `--keep-days 90` — manter últimos 90 dias
- Sem limite `--keep-count` (remover só por data)

Customizável:
```bash
--keep-days 180 --keep-count 50
```
Mantém: últimos 180 dias OU últimas 50 execuções por device (o que for maior).

### Cuidados

❌ **Nunca deleta:**
- `reports/pilot-device-compliance/current/` — último relatório
- `reports/pilot-device-compliance/comparisons/` — comparativos
- `reports/pilot-device-compliance/index.json` — metadados
- Raw JSON (já excluído por `.gitignore`)

✅ **Deleta:**
- `reports/pilot-device-compliance/history/{DEVICE}/*.md` — relatórios antigos

## Exportação — Export to CSV

Exportar índice e metadados para CSV.

### Básico

```bash
python3 tools/local/export_compliance_csv.py
```

**Output:** `compliance-history.csv` (local)

**Colunas:**
- `device` — device name
- `device_id` — NetBox ID
- `last_report` — timestamp (ISO8601)
- `reports_count` — número de execuções

### Com metadados

```bash
python3 tools/local/export_compliance_csv.py \
  --include-metadata \
  --output reports/history-summary.csv
```

**Colunas adicionais:**
- `total_divergences` — último relatório
- `highest_severity` — último relatório
- `status` — último relatório (ok | drift_detected)
- `netbox_loaded` — Sim/Não

### Exemplo CSV

```csv
device,device_id,last_report,reports_count,total_divergences,highest_severity,status,netbox_loaded
4WNET-MNS-KTG-RX,1890,2026-04-28T05:53:48Z,12,2,medium,drift_detected,Sim
ROUTER-A,1891,2026-04-28T14:00:00Z,5,0,info,ok,Não
```

## Fluxo de manutenção — Workflow

### Daily

```bash
# Dry-run cleanup
python3 tools/local/cleanup_compliance_history.py --keep-days 90
```

### Weekly

```bash
# Apply cleanup
python3 tools/local/cleanup_compliance_history.py \
  --keep-days 90 \
  --apply

# Export current state
python3 tools/local/export_compliance_csv.py \
  --include-metadata \
  --output compliance-summary-$(date +%Y-%m-%d).csv
```

### Monthly

```bash
# Archive CSV exports
mkdir -p reports/exports
mv compliance-summary-*.csv reports/exports/

# Create summary report
echo "Total devices:" $(wc -l < compliance-summary.csv)
```

## Segurança — Security

✅ **Read-only:**
- Nunca chama API
- Nunca escreve no NetBox
- Parseamento local de Markdown
- Nenhum raw JSON manipulado

❌ **Nunca:**
- Exporta credenciais
- Exporta payloads brutos
- Altera equipamentos
- Usa /sync

## Futura integração — Future

### Web UI

CSV pode ser carregado na Web UI para:
- Timeline de execuções por device
- Compliance trends
- Divergence tracking

### BI / Analytics

CSV pode ser importado em:
- Grafana (datasource)
- Spreadsheets (Google Sheets, Excel)
- BI tools (Tableau, PowerBI)

Campos recomendados para análise:
- `device` — grouping
- `last_report` — time-series
- `total_divergences` — metrics
- `highest_severity` — severity level
- `reports_count` — activity indicator

### CI Integration

```bash
# .github/workflows/monthly-cleanup.yml
python3 tools/local/cleanup_compliance_history.py \
  --keep-days 90 \
  --apply

python3 tools/local/export_compliance_csv.py \
  --include-metadata
```

## Troubleshooting

**"Error: index not found"**
- Rodar `python3 tools/local/init_report_structure.py` primeiro

**"No reports to delete"**
- Cleanup working correctly (nada antigo o suficiente)

**Atualizar index.json manualmente**
- Não recomendado
- Apenas se um file foi deletado fora do script
- Recompor contagem de reports:
  ```bash
  ls reports/pilot-device-compliance/history/{DEVICE}/ | wc -l
  ```
