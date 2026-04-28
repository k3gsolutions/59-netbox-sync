# Tools — k3g-monitoring-iac

Scripts e utilitários para pipeline compliance NetBox.

## local/

Scripts Python standard library para local archiving, comparação, limpeza.

### Inicializar estrutura

```bash
python3 tools/local/init_report_structure.py [--root .]
```

Cria:
- `reports/pilot-device-compliance/{current,history}/`
- `reports/pilot-device-compliance/index.json`
- `reports/pilot-device-compliance/.gitignore`

### Arquivar relatório

```bash
python3 tools/local/archive_compliance_report.py \
  --report <file.md> \
  --device <DEVICE-NAME> \
  [--device-id <ID>]
```

Fluxo:
1. Lê relatório Markdown
2. Copia para `history/{DEVICE}/{TIMESTAMP}-compliance-report.md`
3. Atualiza `current/{DEVICE}-compliance-report.md`
4. Incrementa contador em `index.json`

Sem secrets: raw JSON ignorado por `.gitignore`.

### Scripts futuros

- `compare_compliance_reports.py` — diff entre execuções
- `cleanup_compliance_history.py` — remover antigos
- `export_compliance_csv.py` — exportar histórico

## Documentação

- `../docs/20-report-history-standard.md` — padrão completo
- `../reports/pilot-device-compliance/README.md` — guia local

## Python Version

Python 3.8+ required. Standard library only:
- `json`, `pathlib`, `re`, `datetime`, `shutil`, `argparse`
