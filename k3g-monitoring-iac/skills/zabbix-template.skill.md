# Skill — Zabbix Template

## Objetivo
Criar e revisar templates Zabbix alinhados ao modelo GitOps e à taxonomia NetBox.

## Quando usar
- Definição de novos templates vendor/role/service/governance.
- Revisões de macros e tags.
- Integração de LLD e triggers.

## Entrada esperada
- Template YAML/JSON ou diff.
- Objetivo do template.
- Roles/criticality envolvidas.
- Dependências (outros templates, macros).

## Saída esperada
- Avaliação de aderência à taxonomia.
- Pontos de risco.
- Sugestões de melhoria.
- Lista de testes (LLD, triggers, macros).
- Atualizações necessárias em documentação.

## Checklist
- [ ] Tags compatíveis com `zabbix/tag_taxonomy.yaml`?
- [ ] Macros documentadas?
- [ ] LLD configurada corretamente?
- [ ] Triggers com severidade coerente?
- [ ] Dependências claras?
- [ ] Templates declarados em Git?
- [ ] Dry-run possível antes de aplicar?
- [ ] Documentação/Runbook atualizado?

## Anti-padrões
- Templates duplicados por cliente.
- Uso de macros hardcoded sem default.
- Triggers sem classificação.
- Dependências não declaradas.