# Fase 1.0 — Relatório Markdown de Compliance

## Objetivo
Gerar um relatório local em Markdown a partir do resultado de `/compliance/analyze`.

## Endpoint
- `POST /compliance/analyze/report`
- Retorna um relatório em `text/plain` com o resultado da análise.

## Seções do relatório
1. Resumo executivo
2. Sumário aplicado no dispositivo
3. Sumário documentado no NetBox
4. Diff agregado
5. Divergências por objeto
6. Warnings
7. Ações recomendadas
8. Observações de segurança

## Limitações
- Não escreve no NetBox.
- Não aplica configuração.
- Não chama `/sync`.
- Não gera comandos de correção.
- Não altera parsers.

## Próxima fase
- Suporte a sugestão de comandos de correção.
- Exportação para Markdown + HTML.
- Relatório de compliance com priorização e severidade detalhada.
