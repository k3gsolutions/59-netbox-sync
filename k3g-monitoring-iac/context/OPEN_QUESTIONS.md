# OPEN_QUESTIONS

- Quais custom fields já existem no NetBox?
- Qual versão atual do NetBox?
- Qual versão atual do N8N?
- Qual padrão atual de descrição nos equipamentos?
- O Zabbix já tem templates Huawei reutilizáveis?
- Qual será o ambiente staging?
- O N8N já possui Postgres/Redis dedicados para audit/DLQ?
- Quais tenants/ISPs entram no MVP?
- Como será feita autenticação dos webhooks NetBox?
- Quais canais Evolution API serão usados para alertas?
- Como será separado MSP/tenant no Grafana?
- Existe inventário completo dos dispositivos Huawei NE8000?
- Qual a periodicidade desejada para relatórios de compliance?
- Qual a lista definitiva de nomes de `escalation_profile` a serem usados?
- Há regras de validação condicional no NetBox para `service_type`/`criticality` quando `monitoring_enabled=true`?
- Qual formato `sla_target` deve seguir em diferentes tenants? (por exemplo, `99.99`, `4h`, `15m`)
- O campo `address_family` será derivado do IP ou definido explicitamente em Zabbix?
- O plugin `netbox-bgp` estará instalado em todos os ambientes? Qual plano de fallback para ambientes sem o plugin?