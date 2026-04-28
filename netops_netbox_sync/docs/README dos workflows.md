# N8N Workflows — Sprint 1

Workflows mínimos para provisionar host Zabbix a partir de evento NetBox.

## Ordem de implementação

1. **wf-error-handler** — primeiro porque outros workflows dependem dele
2. **wf-netbox-router** — entry point
3. **wf-onboard-device** — o coração do sistema
4. **wf-onboard-circuit** — opcional Sprint 1, recomendado para Sprint 2
5. **wf-reconcile** — opcional Sprint 1, mandatório Sprint 2

---

## Credenciais N8N necessárias

Criar antes de importar workflows. Nome **exato** importa (workflows referenciam por nome).

| Nome credencial | Tipo | Campos |
|-----------------|------|--------|
| `netbox-api` | HTTP Header Auth | Name: `Authorization`, Value: `Token <netbox_token>` |
| `zabbix-api` | HTTP Header Auth | Name: `Authorization`, Value: `Bearer <zabbix_api_token>` |
| `postgres-monitoring` | Postgres | host, port, database=`monitoring_audit`, user=`n8n_writer`, password |
| `redis-queue` | Redis | host, port, password (mesma do N8N queue) |
| `evolution-api` | HTTP Header Auth | apikey: `<evolution_api_key>` |

Variáveis de ambiente N8N (settings → environment variables):
```
NETBOX_URL=https://netbox.k3g.internal
NETBOX_WEBHOOK_SECRET=<gerado com openssl rand -hex 32>
ZABBIX_URL=https://zabbix.k3g.internal/api_jsonrpc.php
EVOLUTION_API_URL=https://evolution.k3g.internal
EVOLUTION_INSTANCE_NOC=noc
DRY_RUN=false
```

---

## Convenções dentro dos workflows

1. **Cada workflow tem um único trigger.**
2. **Webhook → roteia em sub-workflows** (não fazer tudo num workflow só).
3. **Toda chamada externa em `Try-Catch`** (Error Trigger node em sub-workflow).
4. **Audit gravado em 2 momentos:** antes da ação (`pending`) e depois (`success|error`).
5. **Dry-run respeitado** via expression `{{ $env.DRY_RUN === 'true' }}`.
6. **Idempotência:** sempre `get → diff → update if changed`. Nunca `delete + create`.
7. **Correlação:** webhook gera `correlation_id` (UUID v4) que segue para todos os sub-workflows.

---

## Smoke test após importar cada workflow

Cada workflow tem seção **"Smoke test"** no final do seu .md. Rodar antes de habilitar webhook NetBox.

---

## Anti-padrões

- ❌ Hardcoded URLs/tokens nos nodes. Usar credentials/env.
- ❌ Workflow sem error handler. Sempre conectar ao `wf-error-handler`.
- ❌ Audit log "às vezes". Sempre.
- ❌ HTTP Request sem timeout. Sempre 10-30s.
- ❌ Esperar resposta NetBox webhook > 10s. Webhook responde 200 imediato; processamento async.
