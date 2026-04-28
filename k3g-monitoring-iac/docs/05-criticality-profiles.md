# 05 — Criticality Profiles

## Objetivo
Alinhar criticidade entre NetBox, Zabbix e runbooks.

## Perfis oficiais
- **platinum**
- **gold**
- **silver**
- **bronze**

### platinum
- Uso recomendado: serviços de alta disponibilidade e clientes críticos.
- Severidade Zabbix: `disaster`
- Intervalo de coleta: `30s`
- SLA target: `99.99%`
- Canal de alerta: `whatsapp_noc_senior`, `phone_call`, `email_engineering`
- Escalonamento: `[0, 5, 15]` minutos
- Exemplos: backbone carrier-transit, peering público, internet de cliente estratégico.

### gold
- Uso recomendado: serviços-chave com SLA elevado.
- Severidade Zabbix: `high`
- Intervalo de coleta: `60s`
- SLA target: `99.95%`
- Canal de alerta: `whatsapp_noc`, `email_noc`
- Escalonamento: `[0, 15, 60]` minutos
- Exemplos: customer-l3vpn, transport de alto valor, infra-backbone.

### silver
- Uso recomendado: serviços padrão monitorados com prioridade média.
- Severidade Zabbix: `average`
- Intervalo de coleta: `120s`
- SLA target: `99.5%`
- Canal de alerta: `whatsapp_noc_group`
- Escalonamento: `[0, 60]` minutos
- Exemplos: customer-internet, cdn-cache, infra-management não crítica.

### bronze
- Uso recomendado: serviços com SLA menos crítico e alertas em lote.
- Severidade Zabbix: `warning`
- Intervalo de coleta: `300s`
- SLA target: `99.0%`
- Canal de alerta: `email_noc_batch`
- Escalonamento: nenhum escalonamento automático adicional
- Exemplos: serviços administrativos, infra-management de baixa prioridade.

> Ver detalhes de polling, severidade e canais em `zabbix/criticality_profiles.yaml`.