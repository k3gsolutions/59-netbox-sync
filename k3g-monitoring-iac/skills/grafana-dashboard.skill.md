# Skill — Grafana Dashboard

## Objetivo
Garantir dashboards provisionadas via GitOps, reusáveis e multi-tenant.

## Quando usar
- Criar nova dashboard base.
- Revisar alterações de dashboards existentes.
- Ajustar RBAC e folders.

## Entrada esperada
- Dashboard JSON/declaração GitOps.
- Objetivo e público-alvo.
- Datasources envolvidos.
- Tags/variáveis esperadas.

## Saída esperada
- Avaliação de reutilização.
- Checklist de tags/variáveis.
- Plano de testes (provisioning, RBAC).
- Atualizações necessárias em docs.

## Checklist
- [ ] Provisioning via `grafana/provisioning/`?
- [ ] Dashboards genéricas (sem replicar por cliente)?
- [ ] Variáveis alinhadas às tags do Zabbix?
- [ ] RBAC definido (`grafana/folders/`)?
- [ ] Multi-tenancy respeitado?
- [ ] Sem segredos no JSON?
- [ ] Documentação atualizada?

## Anti-padrões
- Export manual direto do Grafana sem revisão.
- Dashboards específicas por cliente.
- Dados sensíveis embutidos.
- Falta de versionamento Git.