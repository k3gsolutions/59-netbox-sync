# Prompt — FASE 0: Organização do Projeto no VSCode / Codex / Claude

> **Objetivo:** organizar a FASE 0 do projeto **ISP Observability Automation Framework**, criando documentação, contexto operacional, prompts, skills e ferramentas locais para trabalhar com VSCode, Codex e Claude sem perder contexto entre sessões.  
>
> **Codebase relacionado:** `/Users/keslleykssantos/projects/ativos/59-netbox_sync/netops_netbox_sync`

---

## Prompt para enviar ao VSCode / Codex / Claude

```text
Você é um arquiteto de software sênior e especialista em NetOps, observabilidade, NetBox, Zabbix, Grafana, N8N, GitOps e automação para ISP.

Estamos iniciando a FASE 0 do projeto ISP Observability Automation Framework.

Objetivo desta fase:
Organizar a base documental, operacional e estrutural do projeto para que possamos trabalhar com VSCode, Codex e Claude sem perder contexto, sem precisar reler todo o codebase a cada sessão e sem depender de memória externa da IA.

Caminho do codebase relacionado:
/Users/keslleykssantos/projects/ativos/59-netbox_sync/netops_netbox_sync

Este codebase, netops_netbox_sync, já existe e deve ser tratado como uma ferramenta relacionada, não como o repositório principal da nova plataforma.

Nesta FASE 0, você deve:
- organizar a documentação;
- criar arquivos de contexto;
- criar prompts reutilizáveis;
- criar skills locais;
- criar ferramentas locais simples;
- preparar estrutura GitOps;
- documentar como o netops_netbox_sync se encaixa;
- preparar o projeto para execução faseada.

Esta fase NÃO é para implementar workflows N8N reais ainda.
Esta fase NÃO é para criar automação real no Zabbix/Grafana ainda.
Esta fase NÃO é para alterar produção.
Esta fase NÃO é para modificar o netops_netbox_sync, exceto se for apenas documentação externa apontando para ele.
Esta fase NÃO é para criar um novo serviço FastAPI concorrente com N8N.

# 1. Contexto geral do projeto

Queremos construir uma plataforma de observabilidade automatizada para ISP baseada em:

- NetBox como única Source of Truth técnica;
- N8N como orquestrador de eventos e workflows;
- Zabbix como executor de monitoramento;
- Grafana como visualização data-driven;
- Git como controle de templates, dashboards, taxonomia, workflows e runbooks;
- PostgreSQL para audit log, DLQ e drift reports;
- Redis para fila, retry e cache;
- netops_netbox_sync como ferramenta técnica de auditoria NetBox ⇄ dispositivo.

O projeto possui duas frentes complementares.

## Frente A — netops_netbox_sync

Caminho:
`/Users/keslleykssantos/projects/ativos/59-netbox_sync/netops_netbox_sync`

Função:
- coletar estado aplicado dos roteadores Huawei NE8000;
- ler configuração real do dispositivo;
- gerar DeviceInventory;
- gerar NetBoxInventory;
- comparar NetBox vs dispositivo;
- gerar compliance report;
- gerar Markdown operacional;
- gerar comandos sugeridos para correção;
- apoiar brownfield/backfill;
- auditar divergências entre documentação e configuração aplicada.

Estado atual conhecido:
- FASE 0 do netops_netbox_sync já estabilizou pontos críticos;
- FASE 1 criou o modo Analyze Read-Only;
- existe endpoint `POST /compliance/analyze`;
- existem testes garantindo que o modo analyze não chama `sync_to_netbox` nem `sync_bgp_plugin`;
- o objetivo desse codebase é auditoria/compliance, não orquestração principal do monitoramento.

## Frente B — ISP Observability Automation Framework

Função:
- receber webhooks do NetBox;
- provisionar/atualizar hosts no Zabbix;
- aplicar tags, macros, templates e host groups;
- provisionar dashboards/folders no Grafana;
- auditar drift;
- gerar relatórios de governança;
- manter observabilidade da própria plataforma;
- operar com N8N, GitOps, audit log e DLQ.

Esta FASE 0 deve preparar principalmente a Frente B, mantendo clara a integração com a Frente A.

# 2. Princípios não negociáveis

Crie os documentos e estrutura considerando estes princípios:

1. NetBox é a única fonte da verdade técnica.
2. IXC/ERP/CRM podem alimentar o NetBox, mas não competem como fonte técnica.
3. N8N é o orquestrador principal da automação de monitoramento.
4. netops_netbox_sync é ferramenta de auditoria e compliance NetBox ⇄ dispositivo.
5. Equipamentos são read-only nas fases iniciais.
6. Nenhuma configuração deve ser aplicada automaticamente em equipamento nesta fase.
7. Zabbix/Grafana são projeções do NetBox.
8. Templates, dashboards, taxonomia, workflows e mapas devem ser versionados em Git.
9. Toda automação deve ser idempotente.
10. Dry-run deve existir antes de qualquer escrita real.
11. Toda ação deve gerar audit log.
12. Toda falha relevante deve ir para DLQ ou relatório.
13. A descrição de interface deve ser machine-parseable.
14. Documentação humana fica no NetBox e nos runbooks, não no ifAlias.
15. O projeto deve ser operável por time júnior com runbooks claros.
16. A IA deve trabalhar com arquivos de contexto curtos, sem precisar reler todo o codebase.
17. Toda mudança arquitetural relevante deve gerar ou atualizar ADR.
18. Toda fase deve ter critérios de aceite claros.

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
- preparar o repositório para as próximas fases;
- manter uma separação clara entre documentação, GitOps, N8N, Zabbix, Grafana, NetBox e netops_netbox_sync.

# 4. Tarefa principal

Analise o diretório atual aberto no VSCode.

Se o repositório principal ainda não existir ou estiver vazio, crie a estrutura base chamada:

`k3g-monitoring-iac`

Se já existir estrutura parcial, preserve o que existe e complemente sem destruir.

Não implemente workflows N8N reais ainda.
Não implemente integração Zabbix real ainda.
Não implemente Grafana real ainda.
Não altere código funcional do netops_netbox_sync nesta tarefa.
Não crie um novo microserviço FastAPI.
Não substitua N8N por Python.

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

# 6. Conteúdo mínimo dos arquivos principais

## 6.1 README.md

Deve explicar:

- o que é o projeto;
- o que ele não é;
- arquitetura de alto nível;
- status atual;
- como navegar na documentação;
- qual é a fase atual;
- próximos passos;
- relação com `/Users/keslleykssantos/projects/ativos/59-netbox_sync/netops_netbox_sync`.

Inclua seção:

```markdown
## Relação com netops_netbox_sync

O projeto `netops_netbox_sync` é uma ferramenta complementar de auditoria NetBox ⇄ dispositivo.

Ele não substitui o N8N.

- netops_netbox_sync: coleta estado aplicado, gera compliance e suporta brownfield.
- k3g-monitoring-iac: define padrões, workflows, templates, dashboards, taxonomia e governança.
```

## 6.2 PROJECT_CONTEXT.md

Arquivo curto, para IA ler primeiro.

Deve conter:

- objetivo do projeto;
- stack;
- decisões principais;
- frente A e frente B;
- princípios não negociáveis;
- estado atual;
- próximos passos imediatos.

Mantenha pequeno e direto. Este arquivo deve ser o primeiro arquivo lido por Codex/Claude.

## 6.3 ROADMAP.md

Deve conter as fases:

- Fase 0 — Baseline e organização
- Fase 1 — NetBox como SoT
- Fase 2 — Templates Zabbix
- Fase 3 — N8N Orchestrator
- Fase 4 — Circuitos e Interfaces
- Fase 5 — Reconcile, Drift e Compliance
- Fase 6 — Grafana data-driven
- Fase 7 — Observabilidade da observabilidade
- Fase 8 — DR, Backup e Operação

Para cada fase:

- objetivo;
- entregáveis;
- critérios de aceite;
- status;
- dependências;
- riscos.

## 6.4 PHASE0_BASELINE.md

Checklist operacional da fase 0.

Deve incluir:

```markdown
# FASE 0 — Baseline e organização

## Checklist

- [ ] Exportar inventário atual do Zabbix.
- [ ] Exportar dashboards atuais do Grafana.
- [ ] Mapear NetBox atual.
- [ ] Mapear roles dos equipamentos.
- [ ] Validar versões da stack.
- [ ] Aprovar service_types.
- [ ] Aprovar criticality.
- [ ] Aprovar naming convention.
- [ ] Criar ADRs.
- [ ] Criar repo GitOps.
- [ ] Criar prompts reutilizáveis.
- [ ] Criar skills locais.
- [ ] Criar ferramentas locais básicas.
- [ ] Criar estrutura inicial do monorepo.
- [ ] Documentar relação com netops_netbox_sync.
- [ ] Definir ambiente staging.
- [ ] Definir estratégia de dry-run.
```

## 6.5 context/CURRENT_STATE.md

Deve responder:

- onde estamos;
- o que já foi decidido;
- o que já foi criado;
- o que ainda falta;
- qual a próxima ação recomendada.

Inclua explicitamente:

```markdown
## Estado do netops_netbox_sync

Codebase:
`/Users/keslleykssantos/projects/ativos/59-netbox_sync/netops_netbox_sync`

Uso neste projeto:
- auditoria NetBox ⇄ dispositivo;
- coleta do estado aplicado;
- compliance;
- brownfield;
- sugestão de comandos;
- não é o orquestrador principal de monitoramento.
```

## 6.6 context/SYSTEM_MAP.md

Deve mapear:

```text
NetBox → webhooks → N8N → Zabbix/Grafana/Postgres/Redis
netops_netbox_sync → auditoria NetBox ⇄ dispositivo
Git → templates, dashboards, taxonomia, workflows e docs
```

Inclua um diagrama ASCII.

## 6.7 context/NEXT_ACTIONS.md

Deve conter as próximas 5 a 10 ações pequenas e executáveis.

Sugestão:

```markdown
# Próximas ações

1. Validar estrutura inicial do repositório.
2. Revisar PROJECT_CONTEXT.md.
3. Revisar ROADMAP.md.
4. Confirmar service_types.
5. Confirmar criticality profiles.
6. Confirmar naming convention.
7. Criar scripts de export Zabbix/Grafana.
8. Criar baseline real.
9. Revisar ADRs iniciais.
10. Preparar Sprint 1 dos workflows N8N.
```

## 6.8 context/OPEN_QUESTIONS.md

Deve registrar perguntas em aberto, como:

- Quais custom fields já existem no NetBox?
- Qual versão atual do Zabbix?
- Qual versão atual do Grafana?
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

## 6.9 AGENTS.md

Criar arquivo com instruções para Codex/Claude:

```markdown
# AGENTS.md

## Regra de leitura

Antes de qualquer tarefa, leia:

1. `PROJECT_CONTEXT.md`
2. `context/CURRENT_STATE.md`
3. `context/NEXT_ACTIONS.md`
4. Arquivo específico da tarefa

Não leia o repositório inteiro sem necessidade.

## Regras de execução

- Não implemente nada fora da fase atual.
- Não altere decisões arquiteturais sem criar ADR.
- Não remova documentação existente sem justificar.
- Não chame APIs reais sem autorização explícita.
- Não implemente automação de produção nesta fase.
- Não altere o codebase `netops_netbox_sync` sem solicitação explícita.
- Não crie serviço FastAPI concorrente ao N8N.
- Mantenha separação entre documentação, GitOps, workflows, templates e ferramentas.

## Ao finalizar uma tarefa

Atualize, quando aplicável:

- `context/CURRENT_STATE.md`
- `context/NEXT_ACTIONS.md`
- `CHANGELOG.md`
- `PHASE0_BASELINE.md`
- ADRs, se houver decisão arquitetural

## Uso de prompts

- Code review: `prompts/code-review.md`
- Arquitetura: `prompts/architecture-review.md`
- Workflow N8N: `prompts/n8n-workflow-builder.md`
- Documentação: `prompts/docs-updater.md`
- Resumo de fase: `prompts/phase-summary.md`
```

# 7. Conteúdo dos prompts reutilizáveis

Crie prompts curtos e objetivos em `prompts/`.

## 7.1 prompts/code-review.md

Deve orientar revisão de:

- segurança;
- idempotência;
- dry-run;
- audit log;
- DLQ;
- separação de concerns;
- risco operacional;
- testes;
- documentação;
- rollback;
- vazamento de segredo.

## 7.2 prompts/architecture-review.md

Deve orientar revisão de:

- aderência ao PRD;
- aderência aos ADRs;
- NetBox como SoT;
- N8N como orquestrador;
- separação entre netops_netbox_sync e k3g-monitoring-iac;
- riscos;
- dependências;
- próximos passos.

## 7.3 prompts/n8n-workflow-builder.md

Deve orientar criação/revisão de workflow N8N com:

- input esperado;
- output esperado;
- nodes;
- idempotência;
- dry-run;
- audit log;
- error handler;
- DLQ;
- smoke tests;
- variáveis de ambiente;
- credentials;
- anti-padrões.

## 7.4 prompts/zabbix-template-review.md

Deve orientar revisão de:

- template vendor-base;
- template role;
- template service;
- template governance;
- macros;
- tags;
- LLD;
- preprocessing;
- dependências;
- cardinalidade;
- compatibilidade com tag_taxonomy.

## 7.5 prompts/grafana-dashboard-review.md

Deve orientar revisão de:

- dashboards genéricas;
- variáveis;
- tags Zabbix;
- folders;
- RBAC;
- provisioning;
- remoção de dashboard por cliente;
- compatibilidade com multi-tenancy.

## 7.6 prompts/netbox-data-model-review.md

Deve orientar revisão de:

- custom fields;
- tenants;
- tenant groups;
- device roles;
- sites;
- circuits;
- interfaces;
- L2VPN;
- VRF;
- BGP plugin;
- validação de campos obrigatórios;
- naming convention.

## 7.7 prompts/test-generator.md

Deve orientar criação de testes para:

- scripts locais;
- validação de YAML;
- workflows N8N;
- lint de documentação;
- smoke tests;
- dados fake.

## 7.8 prompts/docs-updater.md

Deve orientar atualização de documentação:

- atualizar contexto;
- atualizar NEXT_ACTIONS;
- atualizar CHANGELOG;
- atualizar ADR se houve decisão;
- não duplicar informação;
- manter documentos curtos.

## 7.9 prompts/phase-summary.md

Deve gerar resumo de fase com:

- objetivo;
- concluído;
- pendente;
- riscos;
- decisões;
- próximos passos.

# 8. Conteúdo das skills

Criar arquivos em `skills/`.

Cada skill deve ter:

- objetivo;
- quando usar;
- entrada esperada;
- saída esperada;
- checklist;
- anti-padrões.

## Skills obrigatórias

1. `skills/code-review.skill.md`
2. `skills/n8n-workflow.skill.md`
3. `skills/zabbix-template.skill.md`
4. `skills/grafana-dashboard.skill.md`
5. `skills/netbox-modeling.skill.md`
6. `skills/compliance-report.skill.md`
7. `skills/documentation-maintenance.skill.md`

Exemplo de conteúdo para `skills/code-review.skill.md`:

```markdown
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
- Misturar coleta, análise e escrita no mesmo fluxo sem separação.
```

# 9. Ferramentas locais

Criar scripts simples em `tools/local/`.

## 9.1 summarize_repo.py

Função:
- listar estrutura do projeto;
- ignorar `.git`, `venv`, `.venv`, `node_modules`, `__pycache__`;
- gerar ou atualizar `context/MEMORY_INDEX.md`;
- não ler arquivos gigantes;
- não incluir segredos.

## 9.2 update_context_index.py

Função:
- varrer arquivos `.md`;
- gerar índice de documentos principais;
- atualizar `context/MEMORY_INDEX.md`;
- indicar tamanho aproximado e finalidade do arquivo.

## 9.3 check_docs_links.py

Função:
- verificar links internos entre arquivos Markdown;
- reportar links quebrados;
- não acessar internet.

## 9.4 lint_markdown.py

Função:
- checar títulos duplicados;
- checar arquivos sem H1;
- checar linhas muito grandes, se simples;
- não ser rígido demais.

## 9.5 generate_phase_report.py

Função:
- ler `ROADMAP.md`, `PHASE0_BASELINE.md` e `context/NEXT_ACTIONS.md`;
- gerar resumo simples em `context/CURRENT_STATE.md` ou arquivo de relatório;
- não sobrescrever conteúdo manual sem backup.

Se não for implementar totalmente os scripts agora, crie os arquivos com docstring clara, argumentos esperados e TODOs.

# 10. Arquivos NetBox iniciais

Criar YAMLs iniciais, ainda sem aplicar em API real.

## netbox/custom-fields/service_type.yaml

Deve conter choices:

```yaml
type: choice
required: true
applies_to:
  - circuit
  - interface
  - l2vpn
choices:
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
```

## netbox/custom-fields/criticality.yaml

```yaml
type: choice
required: true
applies_to:
  - device
  - circuit
  - l2vpn
choices:
  - platinum
  - gold
  - silver
  - bronze
```

## netbox/custom-fields/monitoring_enabled.yaml

```yaml
type: boolean
required: true
default: false
applies_to:
  - device
  - circuit
  - interface
  - l2vpn
```

# 11. Arquivos Zabbix iniciais

Criar stubs com conteúdo útil.

## zabbix/tag_taxonomy.yaml

Deve conter tags permitidas:

```yaml
allowed_tags:
  environment:
    choices: [prod, staging, lab]
  tenant:
    type: slug
    source: netbox.tenant.slug
  service_type:
    source: netbox.custom_fields.service_type
  criticality:
    choices: [platinum, gold, silver, bronze]
  pop:
    type: slug
    source: netbox.site.slug
  device_role:
    choices: [pe, p, rr, olt, sw-access, sw-core, cgnat, bng, mgmt]
  vendor:
    choices: [huawei, juniper, mikrotik, cisco, datacom, raisecom, zte]
  netbox_id:
    type: integer
  circuit_id:
    type: string
    max_length: 32
  alert_class:
    choices: [service, infra, governance, security]
  owner:
    choices: [noc, engineering, backbone, corporativo]
  compliant:
    choices: ["true", "false"]
  vc_id:
    type: integer
  asn_remote:
    type: integer
  address_family:
    choices: [ipv4, ipv6]
```

## zabbix/criticality_profiles.yaml

```yaml
profiles:
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

## zabbix/role_template_map.yaml

Criar um mapa inicial com:

- pe;
- p;
- rr;
- sw-access;
- olt.

Não precisa ter templates reais ainda, mas deve representar o desenho.

# 12. N8N workflows em Markdown

Criar stubs ou consolidar documentação dos workflows em:

- `n8n/workflows/wf-netbox-router.md`
- `n8n/workflows/wf-error-handler.md`
- `n8n/workflows/wf-onboard-device.md`
- `n8n/workflows/wf-onboard-circuit.md`
- `n8n/workflows/wf-reconcile.md`
- `n8n/workflows/wf-compliance-report.md`

Cada arquivo deve ter:

- objetivo;
- trigger;
- input;
- output;
- nodes principais;
- critérios de aceite;
- smoke test;
- riscos;
- anti-padrões.

Não criar JSON real do N8N ainda.

# 13. VSCode

Criar `.vscode/settings.json` com boas práticas:

- trim trailing whitespace;
- format on save para markdown, yaml, json e python, se seguro;
- exclude de venv, node_modules, .git, __pycache__;
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

# 14. O que NÃO fazer nesta fase

- Não implementar workflows N8N reais em JSON ainda.
- Não chamar API real do NetBox.
- Não chamar API real do Zabbix.
- Não chamar API real do Grafana.
- Não criar dashboards Grafana completos.
- Não aplicar configuração em equipamento.
- Não criar integração real de produção.
- Não mexer no projeto `netops_netbox_sync`, exceto para documentar como ele se relaciona com esta plataforma.
- Não criar microserviço FastAPI novo.
- Não substituir N8N por Python.
- Não criar complexidade desnecessária.
- Não inserir segredos em arquivos.
- Não criar token, senha ou URL sensível hardcoded.

# 15. Saída esperada

Ao finalizar, entregue:

1. Resumo do que foi criado.
2. Árvore de diretórios criada.
3. Arquivos principais criados.
4. Arquivos alterados.
5. Conteúdo resumido de:
   - README.md
   - PROJECT_CONTEXT.md
   - ROADMAP.md
   - PHASE0_BASELINE.md
   - AGENTS.md
6. Lista de prompts criados.
7. Lista de skills criadas.
8. Lista de ferramentas locais criadas.
9. Como usar no VSCode.
10. Próximas ações recomendadas.
11. Confirmação de que nenhuma automação real foi implementada ainda.
12. Confirmação de que o codebase `/Users/keslleykssantos/projects/ativos/59-netbox_sync/netops_netbox_sync` não foi alterado.

# 16. Critérios de aceite

A FASE 0 estará bem iniciada quando:

- O projeto abrir no VSCode com estrutura clara.
- A IA souber onde buscar contexto sem reler tudo.
- Existirem prompts reutilizáveis.
- Existirem skills locais para tarefas repetitivas.
- Existir roadmap faseado.
- Existir checklist de baseline.
- Existirem ADRs iniciais.
- Existir separação clara entre:
  - netops_netbox_sync;
  - N8N workflows;
  - Zabbix templates;
  - Grafana dashboards;
  - NetBox model;
  - documentação;
  - ferramentas locais.
- Nenhuma automação real tiver sido aplicada.
- Nenhum segredo tiver sido versionado.
- Nenhuma API real tiver sido chamada.
```

---

## Resposta esperada do VSCode/Codex/Claude

Depois de executar, peça para ele responder somente neste formato:

```text
## Entrega FASE 0 — Organização Inicial

### 1. Resumo

...

### 2. Árvore criada

...

### 3. Arquivos criados

...

### 4. Arquivos alterados

...

### 5. Conteúdo dos principais arquivos

#### README.md
...

#### PROJECT_CONTEXT.md
...

#### ROADMAP.md
...

#### PHASE0_BASELINE.md
...

#### AGENTS.md
...

### 6. Prompts criados

...

### 7. Skills criadas

...

### 8. Ferramentas locais criadas

...

### 9. Como usar no VSCode

...

### 10. Próximas ações

...

### 11. Confirmações

- [ ] Nenhuma automação real foi implementada.
- [ ] Nenhuma API real foi chamada.
- [ ] Nenhum segredo foi criado ou versionado.
- [ ] O codebase netops_netbox_sync não foi alterado.
```

---

## Próxima ação depois da entrega

Após a entrega, revisar especialmente:

1. `PROJECT_CONTEXT.md`
2. `AGENTS.md`
3. `ROADMAP.md`
4. `PHASE0_BASELINE.md`
5. `context/NEXT_ACTIONS.md`
6. `context/MEMORY_INDEX.md`

A revisão deve confirmar se a IA consegue continuar o projeto em outra sessão lendo apenas esses arquivos, sem precisar reabrir todo o codebase.
