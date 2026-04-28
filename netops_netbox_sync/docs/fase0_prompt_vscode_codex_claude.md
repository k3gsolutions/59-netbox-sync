# Prompt para VSCode / Codex / Claude — FASE 0

> Use este prompt no VSCode com Codex ou Claude para organizar a FASE 0 do projeto **ISP Observability Automation Framework**.

---

## Prompt

Você é um arquiteto de software sênior e especialista em NetOps, observabilidade, NetBox, Zabbix, Grafana, N8N, GitOps e automação para ISP.

Estamos iniciando a **FASE 0** do projeto **ISP Observability Automation Framework**.

O objetivo desta fase é organizar a base documental, operacional e estrutural do projeto para que possamos trabalhar com **VSCode, Codex e Claude** sem perder contexto, sem precisar reler todo o codebase a cada sessão e sem depender de memória externa da IA.

Esta fase **NÃO** é para implementar workflows N8N ainda.  
Esta fase **NÃO** é para criar automação real no Zabbix/Grafana ainda.  
Esta fase **NÃO** é para alterar produção.  
Esta fase é para criar a fundação de documentação, contexto, padrões, skills locais, prompts reutilizáveis e estrutura de projeto.

---

# 1. Contexto do projeto

Queremos construir uma plataforma de observabilidade automatizada para ISP baseada em:

- NetBox como única Source of Truth;
- N8N como orquestrador de eventos e workflows;
- Zabbix como executor de monitoramento;
- Grafana como visualização data-driven;
- Git como controle de templates, dashboards, taxonomia e runbooks;
- PostgreSQL para audit log, DLQ e drift reports;
- Redis para fila/retry/cache;
- `netops_netbox_sync` como ferramenta técnica de auditoria NetBox ⇄ dispositivo.

O projeto possui duas frentes:

## Frente A — netops_netbox_sync

Função:

- coletar estado aplicado dos roteadores Huawei NE8000;
- ler configuração real do dispositivo;
- gerar `DeviceInventory`;
- futuramente gerar `NetBoxInventory`;
- comparar NetBox vs dispositivo;
- gerar compliance report;
- gerar Markdown operacional;
- gerar comandos sugeridos para correção;
- apoiar brownfield/backfill.

## Frente B — ISP Observability Automation Framework

Função:

- receber webhooks do NetBox;
- provisionar/atualizar hosts no Zabbix;
- aplicar tags, macros, templates e host groups;
- provisionar dashboards/folders no Grafana;
- auditar drift;
- gerar relatórios de governança;
- manter observabilidade da própria plataforma.

---

# 2. Princípios não negociáveis

Crie os documentos e estrutura considerando estes princípios:

1. NetBox é a única fonte da verdade técnica.
2. IXC/ERP/CRM podem alimentar o NetBox, mas não competem como fonte técnica.
3. N8N é o orquestrador principal da automação de monitoramento.
4. `netops_netbox_sync` é ferramenta de auditoria e compliance NetBox ⇄ dispositivo.
5. Equipamentos são read-only nas fases iniciais.
6. Nenhuma configuração deve ser aplicada automaticamente em equipamento nesta fase.
7. Zabbix/Grafana são projeções do NetBox.
8. Templates, dashboards, taxonomia e mapas devem ser versionados em Git.
9. Toda automação deve ser idempotente.
10. Dry-run deve existir antes de qualquer escrita real.
11. Toda ação deve gerar audit log.
12. Toda falha relevante deve ir para DLQ ou relatório.
13. A descrição de interface deve ser machine-parseable.
14. Documentação humana fica no NetBox e nos runbooks, não no `ifAlias`.
15. O projeto deve ser operável por time júnior com runbooks claros.

---

# 3. Objetivo prático da FASE 0

Criar uma estrutura de projeto/documentação que permita:

- abrir o VSCode e entender rapidamente o projeto;
- trocar entre Codex e Claude sem perder contexto;
- ter arquivos de contexto curtos e objetivos;
- ter prompts reutilizáveis para code review, análise, geração de workflow, testes e documentação;
- ter checklists de execução da fase;
- ter ADRs para decisões arquiteturais;
- ter uma estrutura de skills/tools locais para tarefas repetitivas;
- ter documentação que evite a IA reler todo o codebase;
- preparar o repositório para as próximas fases.

---

# 4. Tarefa principal

Analise o repositório atual e crie uma proposta de organização para a FASE 0.

Se o repositório ainda não existir ou estiver vazio, crie a estrutura base.

Se já existir estrutura parcial, preserve o que existe e complemente sem destruir.

Não implemente workflows N8N reais ainda.  
Não implemente integração Zabbix real ainda.  
Não implemente Grafana real ainda.  
Não altere código funcional do `netops_netbox_sync` nesta tarefa.

---

# 5. Estrutura desejada

Crie ou proponha esta estrutura:

```text
k3g-monitoring-iac/
├── README.md
├── PROJECT_CONTEXT.md
├── ROADMAP.md
├── PHASE0_BASELINE.md
├── DECISIONS.md
├── CHANGELOG.md
├── AGENTS.md
├── docs/
│   ├── 00-overview.md
│   ├── 01-architecture.md
│   ├── 02-phase0-baseline.md
│   ├── 03-naming-convention.md
│   ├── 04-tag-taxonomy.md
│   ├── 05-criticality-profiles.md
│   ├── 06-netbox-sot.md
│   ├── 07-zabbix-templates-strategy.md
│   ├── 08-grafana-strategy.md
│   ├── 09-n8n-workflows-strategy.md
│   ├── 10-brownfield-migration.md
│   ├── 11-operational-runbooks.md
│   ├── 12-observability-of-observability.md
│   └── adr/
│       ├── 0001-netbox-as-single-sot.md
│       ├── 0002-n8n-as-orchestrator.md
│       ├── 0003-machine-parseable-naming.md
│       ├── 0004-gitops-for-monitoring-assets.md
│       └── 0005-read-only-equipment-first.md
├── context/
│   ├── CURRENT_STATE.md
│   ├── SYSTEM_MAP.md
│   ├── OPEN_QUESTIONS.md
│   ├── NEXT_ACTIONS.md
│   ├── GLOSSARY.md
│   └── MEMORY_INDEX.md
├── prompts/
│   ├── README.md
│   ├── code-review.md
│   ├── architecture-review.md
│   ├── n8n-workflow-builder.md
│   ├── zabbix-template-review.md
│   ├── grafana-dashboard-review.md
│   ├── netbox-data-model-review.md
│   ├── test-generator.md
│   ├── docs-updater.md
│   └── phase-summary.md
├── skills/
│   ├── README.md
│   ├── code-review.skill.md
│   ├── n8n-workflow.skill.md
│   ├── zabbix-template.skill.md
│   ├── grafana-dashboard.skill.md
│   ├── netbox-modeling.skill.md
│   ├── compliance-report.skill.md
│   └── documentation-maintenance.skill.md
├── tools/
│   ├── README.md
│   ├── local/
│   │   ├── summarize_repo.py
│   │   ├── update_context_index.py
│   │   ├── check_docs_links.py
│   │   ├── lint_markdown.py
│   │   └── generate_phase_report.py
│   └── schemas/
│       ├── tag_taxonomy.schema.yaml
│       ├── role_template_map.schema.yaml
│       └── criticality_profiles.schema.yaml
├── netbox/
│   ├── README.md
│   ├── custom-fields/
│   │   ├── service_type.yaml
│   │   ├── criticality.yaml
│   │   ├── monitoring_enabled.yaml
│   │   ├── bandwidth_mbps.yaml
│   │   ├── sla_target.yaml
│   │   └── escalation_profile.yaml
│   ├── webhooks.yaml
│   └── tenant-groups.yaml
├── zabbix/
│   ├── README.md
│   ├── role_template_map.yaml
│   ├── tag_taxonomy.yaml
│   ├── criticality_profiles.yaml
│   ├── macros_defaults.yaml
│   └── templates/
│       ├── vendor/
│       ├── role/
│       ├── service/
│       └── governance/
├── grafana/
│   ├── README.md
│   ├── dashboards/
│   │   ├── customer/
│   │   ├── carrier/
│   │   ├── infra/
│   │   ├── noc/
│   │   └── platform/
│   ├── folders/
│   │   └── permissions.yaml
│   └── provisioning/
│       ├── dashboards.yaml
│       └── datasources.yaml
├── n8n/
│   ├── README.md
│   └── workflows/
│       ├── wf-netbox-router.md
│       ├── wf-error-handler.md
│       ├── wf-onboard-device.md
│       ├── wf-onboard-circuit.md
│       ├── wf-reconcile.md
│       └── wf-compliance-report.md
├── scripts/
│   ├── README.md
│   ├── lint_descriptions.py
│   ├── backfill_netbox.py
│   ├── export_zabbix_inventory.py
│   ├── export_grafana_inventory.py
│   └── reconcile_dryrun.py
├── tests/
│   ├── README.md
│   ├── unit/
│   └── integration/
└── .vscode/
    ├── settings.json
    ├── tasks.json
    └── extensions.json
```

---

# 6. Conteúdo mínimo dos arquivos principais

## 6.1 `README.md`

Deve explicar:

- o que é o projeto;
- o que ele não é;
- arquitetura de alto nível;
- status atual;
- como navegar na documentação;
- qual é a fase atual;
- próximos passos.

## 6.2 `PROJECT_CONTEXT.md`

Arquivo curto, para IA ler primeiro.

Deve conter:

- objetivo do projeto;
- stack;
- decisões principais;
- Frente A e Frente B;
- princípios não negociáveis;
- estado atual;
- próximos passos imediatos.

Este arquivo deve ser mantido pequeno e direto.

## 6.3 `ROADMAP.md`

Deve conter as fases:

- Fase 0 — Baseline e organização;
- Fase 1 — NetBox como SoT;
- Fase 2 — Templates Zabbix;
- Fase 3 — N8N Orchestrator;
- Fase 4 — Circuitos e Interfaces;
- Fase 5 — Reconcile, Drift e Compliance;
- Fase 6 — Grafana data-driven;
- Fase 7 — Observabilidade da observabilidade;
- Fase 8 — DR, Backup e Operação.

Para cada fase:

- objetivo;
- entregáveis;
- critérios de aceite;
- status.

## 6.4 `PHASE0_BASELINE.md`

Checklist operacional da fase 0.

Deve incluir:

- [ ] Exportar inventário atual do Zabbix.
- [ ] Exportar dashboards atuais do Grafana.
- [ ] Mapear NetBox atual.
- [ ] Mapear roles dos equipamentos.
- [ ] Validar versões da stack.
- [ ] Aprovar `service_types`.
- [ ] Aprovar `criticality`.
- [ ] Aprovar naming convention.
- [ ] Criar ADRs.
- [ ] Criar repo GitOps.
- [ ] Criar prompts reutilizáveis.
- [ ] Criar skills locais.
- [ ] Criar ferramentas locais básicas.
- [ ] Criar estrutura inicial do monorepo.

## 6.5 `context/CURRENT_STATE.md`

Deve responder:

- onde estamos;
- o que já foi decidido;
- o que já foi criado;
- o que ainda falta;
- qual a próxima ação recomendada.

## 6.6 `context/SYSTEM_MAP.md`

Deve mapear:

```text
NetBox → webhooks → N8N → Zabbix/Grafana/Postgres/Redis
netops_netbox_sync → auditoria NetBox ⇄ dispositivo
Git → templates, dashboards, taxonomia, workflows e docs
```

## 6.7 `context/NEXT_ACTIONS.md`

Deve conter as próximas 5 a 10 ações pequenas e executáveis.

## 6.8 `context/OPEN_QUESTIONS.md`

Deve registrar perguntas em aberto, como:

- Quais custom fields já existem no NetBox?
- Qual versão atual do Zabbix?
- Qual versão atual do Grafana?
- Qual versão atual do NetBox?
- Qual padrão atual de descrição nos equipamentos?
- O Zabbix já tem templates Huawei reutilizáveis?
- Qual será o ambiente staging?
- O N8N já possui Postgres/Redis dedicados para audit/DLQ?
- Quais tenants/ISPs entram no MVP?

---

# 7. Prompts reutilizáveis

Criar arquivos dentro de `prompts/` para:

1. code review;
2. arquitetura;
3. criação de workflow N8N;
4. revisão de template Zabbix;
5. revisão de dashboard Grafana;
6. modelagem NetBox;
7. geração de testes;
8. atualização de documentação;
9. resumo de fase.

Cada prompt deve ser curto, objetivo e orientado a tarefa.

## 7.1 `prompts/code-review.md`

Deve orientar revisão sobre:

- segurança;
- idempotência;
- dry-run;
- audit log;
- separação de concerns;
- risco operacional;
- testes;
- documentação.

## 7.2 `prompts/architecture-review.md`

Deve orientar revisão sobre:

- aderência ao PRD;
- aderência aos ADRs;
- riscos de acoplamento;
- dependências externas;
- pontos de falha;
- evolução incremental;
- anti-padrões.

## 7.3 `prompts/n8n-workflow-builder.md`

Deve orientar criação/revisão de workflows com:

- um trigger por workflow;
- HMAC em webhooks;
- correlation_id;
- audit log;
- DLQ;
- dry-run;
- idempotência;
- credenciais via N8N credentials/env;
- nada hardcoded.

---

# 8. Skills locais

Criar arquivos de skill em Markdown, cada um com:

- objetivo;
- quando usar;
- entrada esperada;
- saída esperada;
- checklist;
- anti-padrões.

Exemplos:

- `skills/code-review.skill.md`
- `skills/n8n-workflow.skill.md`
- `skills/zabbix-template.skill.md`
- `skills/grafana-dashboard.skill.md`
- `skills/netbox-modeling.skill.md`
- `skills/compliance-report.skill.md`
- `skills/documentation-maintenance.skill.md`

## 8.1 Exemplo de conteúdo para `skills/code-review.skill.md`

A skill deve orientar a IA a revisar:

- segurança;
- idempotência;
- dry-run;
- audit log;
- separação de concerns;
- risco operacional;
- testes;
- documentação;
- impacto em produção;
- aderência ao roadmap.

---

# 9. Ferramentas locais

Criar scripts locais simples, se possível, mas sem complexidade desnecessária.

Prioridade:

## 9.1 `tools/local/summarize_repo.py`

Objetivo:

- listar estrutura do projeto;
- ignorar `venv`, `node_modules`, `.git`, `__pycache__`;
- gerar `context/MEMORY_INDEX.md`.

## 9.2 `tools/local/update_context_index.py`

Objetivo:

- atualizar índice de documentos importantes;
- listar arquivos relevantes por área;
- ajudar a IA a não reler tudo.

## 9.3 `tools/local/check_docs_links.py`

Objetivo:

- verificar links internos quebrados em Markdown.

## 9.4 `tools/local/generate_phase_report.py`

Objetivo:

- gerar resumo simples da fase atual baseado em `ROADMAP.md` e `context/NEXT_ACTIONS.md`.

Se não for implementar os scripts agora, crie os arquivos com docstring e TODO claro.

---

# 10. Integração com VSCode

Criar `.vscode/settings.json` com boas práticas:

- trim trailing whitespace;
- format on save para Markdown, YAML, JSON e Python, se seguro;
- exclude de `venv`, `node_modules`, `.git`, `__pycache__`;
- file nesting opcional.

Criar `.vscode/tasks.json` com tarefas:

- `Docs: check links`
- `Context: update memory index`
- `Project: summarize repo`
- `Phase: generate report`

As tarefas podem chamar scripts em `tools/local/`.

Criar `.vscode/extensions.json` recomendando extensões:

- Python;
- YAML;
- Markdown All in One;
- markdownlint;
- Docker;
- REST Client;
- GitLens.

---

# 11. Regras para IA dentro do projeto

Criar o arquivo:

```text
AGENTS.md
```

Com instruções para Codex/Claude:

- Sempre leia primeiro `PROJECT_CONTEXT.md`.
- Depois leia `context/CURRENT_STATE.md`.
- Depois leia `context/NEXT_ACTIONS.md`.
- Não leia o repositório inteiro sem necessidade.
- Não implemente nada fora da fase atual.
- Não altere decisões arquiteturais sem criar ADR.
- Não remova documentação existente sem justificar.
- Ao finalizar tarefa, atualizar:
  - `context/CURRENT_STATE.md`
  - `context/NEXT_ACTIONS.md`
  - `CHANGELOG.md`
- Para code review, usar `prompts/code-review.md`.
- Para workflow N8N, usar `prompts/n8n-workflow-builder.md`.
- Para documentação, usar `prompts/docs-updater.md`.

---

# 12. Conteúdo esperado dos ADRs iniciais

## 12.1 `docs/adr/0001-netbox-as-single-sot.md`

Deve registrar:

- decisão: NetBox é a única fonte da verdade técnica;
- contexto: múltiplas fontes geram divergência;
- consequências positivas;
- consequências negativas;
- alternativas consideradas.

## 12.2 `docs/adr/0002-n8n-as-orchestrator.md`

Deve registrar:

- decisão: N8N será o orquestrador da automação de monitoramento;
- motivo: stack já usada, fácil manutenção por time júnior, baixo atrito operacional;
- consequência: scripts Python ficam para tarefas locais/backfill/compliance;
- alternativa rejeitada: criar microserviço FastAPI concorrente agora.

## 12.3 `docs/adr/0003-machine-parseable-naming.md`

Deve registrar:

- decisão: descrição de interface será slug machine-parseable;
- formato: `<service_type>:<tenant_slug>:NB-<id>[:extra]`;
- motivo: reduzir fragilidade de regex textual humana;
- consequência: documentação humana fica no NetBox.

## 12.4 `docs/adr/0004-gitops-for-monitoring-assets.md`

Deve registrar:

- decisão: templates, dashboards, taxonomia, workflows e schemas serão versionados em Git;
- motivo: auditabilidade, revisão, rollback e padronização;
- consequência: evitar edição manual direta em produção.

## 12.5 `docs/adr/0005-read-only-equipment-first.md`

Deve registrar:

- decisão: equipamentos serão read-only nas fases iniciais;
- motivo: reduzir risco operacional;
- consequência: comandos sugeridos podem ser gerados, mas aplicação depende de validação humana.

---

# 13. Modelos iniciais de YAML

Criar arquivos iniciais, mesmo que ainda simples.

## 13.1 `zabbix/tag_taxonomy.yaml`

Deve conter chaves permitidas, por exemplo:

```yaml
authorized_tags:
  environment:
    values: [prod, staging, lab]
  tenant:
    type: slug
    source: netbox.tenant.slug
  service_type:
    values:
      - customer-internet
      - customer-l2vpn
      - customer-l3vpn
      - customer-transport
      - carrier-transit
      - carrier-peering
      - ix-public
      - cdn-cache
      - infra-backbone
      - infra-management
  criticality:
    values: [platinum, gold, silver, bronze]
  pop:
    type: slug
    source: netbox.site.slug
  device_role:
    values: [pe, p, rr, olt, sw-access, sw-core, cgnat, bng, mgmt]
  vendor:
    values: [huawei, juniper, mikrotik, cisco, datacom, raisecom, zte]
  netbox_id:
    type: integer
  circuit_id:
    type: string
  alert_class:
    values: [service, infra, governance, security]
  owner:
    values: [noc, engineering, backbone, corporativo]
  compliant:
    values: [true, false]
  vc_id:
    type: integer
  asn_remote:
    type: integer
  address_family:
    values: [ipv4, ipv6]
```

## 13.2 `zabbix/criticality_profiles.yaml`

Deve conter:

```yaml
criticality_profiles:
  platinum:
    poll_interval: 30s
    trigger_severity: disaster
    sla_target_pct: 99.99
    alert_channels:
      - whatsapp_noc_senior
      - phone_call
      - email_engineering
    escalation_minutes: [0, 5, 15]
  gold:
    poll_interval: 60s
    trigger_severity: high
    sla_target_pct: 99.95
    alert_channels:
      - whatsapp_noc
      - email_noc
    escalation_minutes: [0, 15, 60]
  silver:
    poll_interval: 120s
    trigger_severity: average
    sla_target_pct: 99.5
    alert_channels:
      - whatsapp_noc_group
    escalation_minutes: [0, 60]
  bronze:
    poll_interval: 300s
    trigger_severity: warning
    sla_target_pct: 99.0
    alert_channels:
      - email_noc_batch
    escalation_minutes: []
```

## 13.3 `zabbix/role_template_map.yaml`

Deve conter estrutura inicial:

```yaml
roles:
  pe:
    base_by_vendor:
      huawei: T_HUAWEI_NE8000_BASE
      juniper: T_JUNIPER_MX_BASE
    role: T_ROLE_PE
    services:
      - T_SVC_BGP_PEERING
      - T_SVC_L2VPN_VPWS
      - T_SVC_L3VPN_VRF
      - T_SVC_INTERFACE_CUSTOMER
      - T_SVC_INTERFACE_CARRIER
    governance:
      - T_GOV_NAMING_COMPLIANCE

  p:
    base_by_vendor:
      huawei: T_HUAWEI_NE8000_BASE
    role: T_ROLE_P
    services: []
    governance:
      - T_GOV_NAMING_COMPLIANCE

  rr:
    base_by_vendor:
      huawei: T_HUAWEI_NE8000_BASE
    role: T_ROLE_RR
    services:
      - T_SVC_BGP_PEERING
    governance:
      - T_GOV_NAMING_COMPLIANCE

  sw-access:
    base_by_vendor:
      huawei: T_HUAWEI_S6730_BASE
      mikrotik: T_MIKROTIK_ROS_BASE
    role: T_ROLE_SW_ACCESS
    services:
      - T_SVC_INTERFACE_CUSTOMER
    governance:
      - T_GOV_NAMING_COMPLIANCE
```

---

# 14. O que NÃO fazer nesta fase

- Não implementar workflows N8N reais em JSON ainda.
- Não chamar API real do NetBox.
- Não chamar API real do Zabbix.
- Não criar dashboards Grafana completos.
- Não aplicar configuração em equipamento.
- Não criar integração real de produção.
- Não mexer no projeto `netops_netbox_sync`, exceto para documentar como ele se relaciona com esta plataforma.
- Não criar microserviço FastAPI novo.
- Não substituir N8N por Python.
- Não criar complexidade desnecessária.

---

# 15. Saída esperada

Entregue:

1. Resumo do que foi criado.
2. Árvore de diretórios criada.
3. Arquivos principais criados.
4. Conteúdo resumido de:
   - `README.md`
   - `PROJECT_CONTEXT.md`
   - `ROADMAP.md`
   - `PHASE0_BASELINE.md`
   - `AGENTS.md`
5. Lista de prompts criados.
6. Lista de skills criadas.
7. Lista de ferramentas locais criadas.
8. Como usar no VSCode.
9. Próximas ações recomendadas.
10. Confirmação de que nenhuma automação real foi implementada ainda.

---

# 16. Critério de aceite

A FASE 0 estará bem iniciada quando:

- O projeto abrir no VSCode com estrutura clara.
- A IA souber onde buscar contexto sem reler tudo.
- Existirem prompts reutilizáveis.
- Existirem skills locais para tarefas repetitivas.
- Existir roadmap faseado.
- Existir checklist de baseline.
- Existirem ADRs iniciais.
- Existir separação clara entre:
  - `netops_netbox_sync`;
  - N8N workflows;
  - Zabbix templates;
  - Grafana dashboards;
  - NetBox model;
  - documentação;
  - ferramentas locais.

---

# 17. Ao finalizar

Ao concluir, entregue somente:

1. árvore criada;
2. arquivos criados;
3. arquivos alterados;
4. conteúdo dos principais arquivos;
5. próximos passos.

Não implemente nenhuma automação real nesta fase.
