# Skill — Compliance Report

## Objetivo
Planejar e revisar relatórios de compliance e drift.

## Quando usar
- Criar relatórios a partir de `netops_netbox_sync`.
- Consolidar divergências NetBox ⇄ dispositivos.
- Preparar reports de auditoria.

## Entrada esperada
- Inventário NetBox vs dispositivo.
- Relatórios ou resultados de `netops_netbox_sync`.
- Critérios de compliance.

## Saída esperada
- Resumo de divergências.
- Prioridades (criticality).
- Recomendações de correção.
- Atualização de runbooks/registros.

## Checklist
- [ ] Dados coletados via ferramenta confiável?
- [ ] Relatório classifica por criticidade?
- [ ] Sugestões de correção documentadas?
- [ ] Integração com DLQ/audit log?
- [ ] Sem escrita direta em equipamento?
- [ ] Documentação atualizada?

## Anti-padrões
- Aplicar correções sem validação.
- Misturar auditoria com execução.
- Ignorar divergências críticas.