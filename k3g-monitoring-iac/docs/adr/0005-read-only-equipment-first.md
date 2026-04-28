# ADR 0005 — Equipamentos read-only nas fases iniciais

## Status
Aceito — Fase 0

## Contexto
A automação ainda está sendo estruturada; aplicar configurações automaticamente gera risco elevado.

## Decisão
Todas as interações com equipamentos permanecem read-only até que runbooks, testes e auditorias estejam consolidados.

## Consequências
- Sem escrita automática em dispositivos nesta fase.
- Necessidade de dry-run e aprovação manual antes de push.
- Auditoria feita com `netops_netbox_sync` e relatórios.

## Referências
- `PHASE0_BASELINE.md`
- `docs/10-brownfield-migration.md`