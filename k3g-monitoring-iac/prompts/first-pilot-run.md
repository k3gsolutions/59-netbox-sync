# Prompt — First Pilot Run

## Objetivo
Orientar a IA durante a execução real do primeiro piloto de compliance, garantindo que o runbook seja seguido e que nenhuma ação não autorizada seja tomada.

## Instruções
- Verifique o runbook em `docs/19-first-pilot-runbook.md` antes de qualquer ação.
- Peça confirmação explícita antes de usar NetBox ou equipamento.
- Nunca chame `/sync`.
- Não conectar em equipamento ou usar API real sem autorização explícita.
- Salve evidências em `reports/pilot-device-compliance/`.
- Sanitizar segredos antes de gravar ou versionar arquivos.
- Atualizar contexto após a execução.

## Fluxo de trabalho
1. Confirmar o escopo do dispositivo piloto.
2. Validar que as credenciais e tokens são read-only.
3. Validar health do endpoint local do netops_netbox_sync.
4. Executar `curl /compliance/analyze` com payload aprovado.
5. Salvar o JSON bruto em `reports/pilot-device-compliance/<device_name>-raw-analyze.json`.
6. Gerar o relatório Markdown para `reports/pilot-device-compliance/<device_name>-compliance-report.md`.
7. Revisar manualmente e documentar lições aprendidas.

## Regras importantes
- Não chamar `/sync`.
- Não executar comandos que gravem no equipamento.
- Não executar endpoints que escrevam no NetBox.
- Não armazenar segredos não sanitizados.
- Não criar automação Zabbix/Grafana nesta fase.
