# Skill — Code Review Operacional

## Objetivo
Revisar mudanças com foco em segurança operacional, idempotência, dry-run, auditabilidade e aderência ao PRD.

## Quando usar
- Antes de mergear mudança.
- Depois de criar workflow N8N.
- Depois de criar script local.
- Depois de alterar template ou dashboard.
- Antes de habilitar escrita em Zabbix/Grafana.

## Entrada esperada
- Diff ou lista de arquivos alterados.
- Objetivo da mudança.
- Fase atual.
- Critérios de aceite.

## Saída esperada
- Resumo da mudança.
- Riscos.
- Problemas críticos.
- Problemas médios.
- Itens menores.
- Testes recomendados.
- Aprovar ou bloquear.

## Checklist
- [ ] Respeita NetBox como SoT?
- [ ] Mantém N8N como orquestrador?
- [ ] É idempotente?
- [ ] Tem dry-run?
- [ ] Tem audit log?
- [ ] Tem tratamento de erro?
- [ ] Evita vazamento de segredo?
- [ ] Não faz escrita indevida em equipamento?
- [ ] Tem testes ou smoke tests?
- [ ] Documentação foi atualizada?

## Anti-padrões
- Escrever direto em produção sem dry-run.
- Criar dashboard por cliente.
- Hardcodar token.
- Criar host Zabbix sem NetBox.
- Ignorar DLQ.
- Misturar coleta, análise e escrita no mesmo fluxo.