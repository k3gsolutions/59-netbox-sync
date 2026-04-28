# Workflow — Error Handler

## Objetivo
Centralizar tratamento de erros, DLQ e alertas provenientes de workflows N8N.

## Trigger
- Webhook interno ou chamada `Execute Workflow` a partir de outros fluxos.

## Input esperado
- Detalhes do erro (workflow origem, payload, stack trace).
- Contexto operacional (criticidade, tenant).

## Output esperado
- Registro em DLQ (PostgreSQL/Redis).
- Notificação (Slack/WhatsApp/E-mail) conforme criticidade.
- Atualização de audit log.

## Nodes principais
1. Validate error payload.
2. Persist in DLQ.
3. Notify via channels.
4. Escalar se necessário.
5. Acknowledgment para workflow origem.

## Critérios de aceite
- Suporte a múltiplas origens.
- Registro completo no audit log.
- Evitar loops de erro.

## Smoke test
- Injetar erro fake e validar registro + notificação.

## Riscos
- Volume alto de erros.
- Falha ao notificar.

## Anti-padrões
- Engolir erros silenciosamente.
- Não registrar contexto.
