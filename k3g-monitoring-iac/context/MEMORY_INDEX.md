# Memory Index
Gerado em: 2026-04-28 10:45:03 UTC
## Arquivos de contexto
| Arquivo | Finalidade provável |
| --- | --- |
| README.md | Visão geral do projeto |
| PROJECT_CONTEXT.md | Contexto rápido para agentes/IA |
| ROADMAP.md | Planejamento faseado |
| PHASE0_BASELINE.md | Checklist operacional da fase |
| AGENTS.md | Regras de atuação para agentes de IA |
| context/CURRENT_STATE.md | Current State — FASE 1.7 (State Management Complete) |
| context/GLOSSARY.md | GLOSSARY |
| context/NEXT_ACTIONS.md | Next Actions — FASE 1.7+ |
| context/OPEN_QUESTIONS.md | OPEN_QUESTIONS |
| context/PHASE_1_ROADMAP.md | FASE 1 Roadmap — Report Tooling |
| context/SYSTEM_MAP.md | SYSTEM_MAP |

## Documentação
| Arquivo | Finalidade provável |
| --- | --- |
| docs/00-overview.md | 00 — Projeto ISP Observability Automation Framework |
| docs/01-architecture.md | 01 — Arquitetura |
| docs/02-phase0-baseline.md | 02 — Fase 0 Baseline |
| docs/03-naming-convention.md | 03 — Naming Convention |
| docs/04-tag-taxonomy.md | 04 — Tag Taxonomy |
| docs/05-criticality-profiles.md | 05 — Criticality Profiles |
| docs/06-netbox-sot.md | 06 — NetBox como SoT |
| docs/07-zabbix-templates-strategy.md | 07 — Estratégia de Templates Zabbix |
| docs/08-grafana-strategy.md | 08 — Estratégia Grafana |
| docs/09-n8n-workflows-strategy.md | 09 — Estratégia de Workflows N8N |
| docs/10-brownfield-migration.md | 10 — Brownfield Migration |
| docs/11-operational-runbooks.md | 11 — Operational Runbooks |
| docs/12-observability-of-observability.md | 12 — Observability of Observability |
| docs/13-ai-operating-model.md | 13 — AI Operating Model |
| docs/14-device-config-discovery-standard.md | 14 — Device Config Discovery Standard |
| docs/15-service-type-dependency-matrix.md | 15 — Service Type Dependency Matrix |
| docs/16-netbox-readiness-checklist.md | 16 — NetBox Readiness Checklist |
| docs/17-pilot-device-compliance-plan.md | 17 — Pilot Device Compliance Plan |
| docs/18-compliance-divergence-catalog.md | 18 — Compliance Divergence Catalog |
| docs/19-first-pilot-runbook.md | Runbook — Primeiro Piloto de Compliance |
| docs/20-report-history-standard.md | Report History Standard — Compliance v1.1 |
| docs/21-netbox-staged-import-strategy.md | NetBox Staged Import Strategy |
| docs/22-compliance-history-maintenance.md | Compliance History Maintenance — v1.0 |
| docs/23-approval-workflow-design.md | Approval Workflow Design — FASE 1.4 |
| docs/24-approval-record-schema.md | ApprovalRecord Schema — FASE 1.4 |
| docs/25-approval-dry-run.md | Approval Dry-Run — FASE 1.5 |
| docs/26-approval-state-management.md | Approval State Management — FASE 1.7 |
| docs/FASE_0_8_1_NETBOX_DEEP_MAPPING.md | Objetivo |
| docs/adr/0001-netbox-as-single-sot.md | ADR 0001 — NetBox como single source of truth técnico |
| docs/adr/0002-n8n-as-orchestrator.md | ADR 0002 — N8N como orquestrador principal |
| docs/adr/0003-machine-parseable-naming.md | ADR 0003 — Naming e descrições machine-parseable |
| docs/adr/0004-gitops-for-monitoring-assets.md | ADR 0004 — GitOps para ativos de monitoramento |
| docs/adr/0005-read-only-equipment-first.md | ADR 0005 — Equipamentos read-only nas fases iniciais |

## Prompts
| Arquivo | Finalidade provável |
| --- | --- |
| prompts/README.md | Prompts — Guia de uso |
| prompts/approval-workflow-review.md | Approval Workflow Review Prompt |
| prompts/architecture-review.md | Prompt — Architecture Review |
| prompts/code-review.md | Prompt — Code Review Operacional |
| prompts/docs-updater.md | Prompt — Docs Updater |
| prompts/first-pilot-run.md | Prompt — First Pilot Run |
| prompts/grafana-dashboard-review.md | Prompt — Grafana Dashboard Review |
| prompts/n8n-workflow-builder.md | Prompt — N8N Workflow Builder |
| prompts/netbox-data-model-review.md | Prompt — NetBox Data Model Review |
| prompts/phase-summary.md | Prompt — Phase Summary |
| prompts/pilot-device-compliance.md | Prompt — Pilot Device Compliance |
| prompts/test-generator.md | Prompt — Test Generator |
| prompts/zabbix-template-review.md | Prompt — Zabbix Template Review |

## Skills
| Arquivo | Finalidade provável |
| --- | --- |
| skills/README.md | Skills — Guia de uso |
| skills/approval-workflow.skill.md | Skill: Approval Workflow |
| skills/code-review.skill.md | Skill — Code Review Operacional |
| skills/compliance-report.skill.md | Skill — Compliance Report |
| skills/documentation-maintenance.skill.md | Skill — Documentation Maintenance |
| skills/grafana-dashboard.skill.md | Skill — Grafana Dashboard |
| skills/n8n-workflow.skill.md | Skill — N8N Workflow |
| skills/netbox-modeling.skill.md | Skill — NetBox Modeling |
| skills/pilot-compliance.skill.md | Skill — Pilot Compliance |
| skills/zabbix-template.skill.md | Skill — Zabbix Template |

## Configurações GitOps
| Arquivo | Finalidade provável |
| --- | --- |
| netbox/custom-fields/bandwidth_mbps.yaml | Configuração declarativa (Bandwidth Mbps) |
| netbox/custom-fields/criticality.yaml | Configuração declarativa (Criticality) |
| netbox/custom-fields/escalation_profile.yaml | Configuração declarativa (Escalation Profile) |
| netbox/custom-fields/monitoring_enabled.yaml | Configuração declarativa (Monitoring Enabled) |
| netbox/custom-fields/service_type.yaml | Configuração declarativa (Service Type) |
| netbox/custom-fields/sla_target.yaml | Configuração declarativa (Sla Target) |
| netbox/tenant-groups.yaml | Configuração declarativa (Tenant-Groups) |
| netbox/webhooks.yaml | Configuração declarativa (Webhooks) |
| zabbix/criticality_profiles.yaml | Configuração declarativa (Criticality Profiles) |
| zabbix/macros_defaults.yaml | Configuração declarativa (Macros Defaults) |
| zabbix/role_template_map.yaml | Configuração declarativa (Role Template Map) |
| zabbix/tag_taxonomy.yaml | Configuração declarativa (Tag Taxonomy) |
| grafana/folders/permissions.yaml | Configuração declarativa (Permissions) |
| grafana/provisioning/dashboards.yaml | Configuração declarativa (Dashboards) |
| grafana/provisioning/datasources.yaml | Configuração declarativa (Datasources) |

## Workflows N8N
| Arquivo | Finalidade provável |
| --- | --- |
| n8n/workflows/wf-compliance-report.md | Workflow — Compliance Report |
| n8n/workflows/wf-error-handler.md | Workflow — Error Handler |
| n8n/workflows/wf-netbox-router.md | Workflow — NetBox Router Event |
| n8n/workflows/wf-onboard-circuit.md | Workflow — Onboard Circuit |
| n8n/workflows/wf-onboard-device.md | Workflow — Onboard Device |
| n8n/workflows/wf-reconcile.md | Workflow — Reconcile |

## Observações
- Diretórios ignorados: .git, .venv, __pycache__, backups, build, dist, node_modules, venv
- Nenhum conteúdo sensível foi exibido.

<!-- AUTO-GENERATED:START -->
## Índice detalhado (auto)
| Arquivo | Título | Seções (H2) | Linhas |
| --- | --- | --- | --- |
| context/CURRENT_STATE.md | Current State — FASE 1.7 (State Management Complete) | Completed; In Progress; Blocked; Known Limitations; Metrics | 198 |
| context/GLOSSARY.md | GLOSSARY | - | 12 |
| context/NEXT_ACTIONS.md | Next Actions — FASE 1.7+ | FASE 1.6 Complete ✅; FASE 1.7 Complete ✅; FASE 1.7.1 — `/compliance/approve` HTTP Endpoint; FASE 1.7.1 — Batch Generation Script; FASE 1.8 — CI Integration | 170 |
| context/OPEN_QUESTIONS.md | OPEN_QUESTIONS | - | 20 |
| context/PHASE_1_ROADMAP.md | FASE 1 Roadmap — Report Tooling | FASE 1.0 ✅ Core Analysis; FASE 1.1 ✅ Report History; FASE 1.2 ✅ Report Comparison & Cleanup; FASE 1.3 ✅ ImportPlan Read-Only; FASE 1.4 Web UI Prototype | 103 |
| context/SYSTEM_MAP.md | SYSTEM_MAP | - | 29 |
| docs/00-overview.md | 00 — Projeto ISP Observability Automation Framework | Objetivo; Pilares principais; Estrutura de documentação | 16 |
| docs/01-architecture.md | 01 — Arquitetura | Visão macro; Componentes; Princípios arquiteturais; Integrações planejadas | 31 |
| docs/02-phase0-baseline.md | 02 — Fase 0 Baseline | Objetivo; Entregáveis; Critérios de aceite; Dependências | 21 |
| docs/03-naming-convention.md | 03 — Naming Convention | Princípios; Convenções iniciais (placeholder) | 13 |
| docs/04-tag-taxonomy.md | 04 — Tag Taxonomy | Objetivo; Estrutura base; Service types oficiais; Matriz de service_type; Observações | 49 |
| docs/05-criticality-profiles.md | 05 — Criticality Profiles | Objetivo; Perfis oficiais | 48 |
| docs/06-netbox-sot.md | 06 — NetBox como SoT | Diretrizes; Ações Fase 0; Relação com netops_netbox_sync; Regras mínimas para monitoramento | 47 |
| docs/07-zabbix-templates-strategy.md | 07 — Estratégia de Templates Zabbix | Objetivo; Diretrizes iniciais; Próximos passos | 15 |
| docs/08-grafana-strategy.md | 08 — Estratégia Grafana | Objetivo; Diretrizes iniciais; Próximos passos | 14 |
| docs/09-n8n-workflows-strategy.md | 09 — Estratégia de Workflows N8N | Objetivo; Diretrizes; Próximos passos | 14 |
| docs/10-brownfield-migration.md | 10 — Brownfield Migration | Contexto; Estratégia; Riscos | 19 |
| docs/11-operational-runbooks.md | 11 — Operational Runbooks | Objetivo; Estrutura sugerida; Status | 14 |
| docs/12-observability-of-observability.md | 12 — Observability of Observability | Objetivo; Diretrizes; Próximos passos | 13 |
| docs/13-ai-operating-model.md | 13 — AI Operating Model | 1. Propósito; 2. Ordem recomendada de leitura; 3. Uso de prompts reutilizáveis; 4. Uso de skills locais; 5. Uso de ferramentas locais (`tools/local/`) | 84 |
| docs/14-device-config-discovery-standard.md | 14 — Device Config Discovery Standard | 1. Objetivo; 2. Escopo inicial; 3. Fonte da verdade; 4. Relação com netops_netbox_sync; 5. Naming convention oficial | 214 |
| docs/15-service-type-dependency-matrix.md | 15 — Service Type Dependency Matrix | customer-internet; customer-l2vpn; customer-l3vpn; customer-transport; carrier-transit | 240 |
| docs/16-netbox-readiness-checklist.md | 16 — NetBox Readiness Checklist | Objetivo; Campos obrigatórios em Device; Campos obrigatórios em Interface; Campos obrigatórios em Circuit; Campos obrigatórios em VRF | 114 |
| docs/17-pilot-device-compliance-plan.md | 17 — Pilot Device Compliance Plan | Objetivo do piloto; Como escolher o dispositivo; Pré-requisitos; Dados necessários; Fluxo de execução | 85 |
| docs/18-compliance-divergence-catalog.md | 18 — Compliance Divergence Catalog | Estrutura do catálogo; Códigos de divergência | 198 |
| docs/19-first-pilot-runbook.md | Runbook — Primeiro Piloto de Compliance | 1. Objetivo; 2. Escopo inicial; 3. Pré-requisitos; 4. Dados a preencher antes da execução; 5. Checklist de segurança | 206 |
| docs/20-report-history-standard.md | Report History Standard — Compliance v1.1 | Objetivo; Estrutura de diretórios; Naming Convention; Index.json Format; Regras de Retenção | 147 |
| docs/21-netbox-staged-import-strategy.md | NetBox Staged Import Strategy | Princípio; Objetivo; Fluxo; Regra obrigatória de nomenclatura; Regra de ouro | 256 |
| docs/22-compliance-history-maintenance.md | Compliance History Maintenance — v1.0 | Limpeza — Cleanup; Exportação — Export to CSV; Fluxo de manutenção — Workflow; Segurança — Security; Futura integração — Future | 195 |
| docs/23-approval-workflow-design.md | Approval Workflow Design — FASE 1.4 | 1. Princípio; 2. Objetivo; 3. Estados da proposta; 4. Ações permitidas; 5. Campos mínimos do ApprovalRecord | 398 |
| docs/24-approval-record-schema.md | ApprovalRecord Schema — FASE 1.4 | Modelo JSON completo; Estrutura por seção; Exemplos; Campos obrigatórios; Campos PROIBIDOS | 529 |
| docs/25-approval-dry-run.md | Approval Dry-Run — FASE 1.5 | Visão geral; Ferramenta 1: create_approval_record.py; Ferramenta 2: render_approval_summary.py; 1. Proposta; 2. Evidência | 364 |
| docs/26-approval-state-management.md | Approval State Management — FASE 1.7 | Estados e Transições; Movimentação de Arquivos; Script: manage_approval_state.py; Estrutura de ApprovalRecord; Validações | 318 |
| docs/FASE_0_8_1_NETBOX_DEEP_MAPPING.md | Fase 0 8 1 Netbox Deep Mapping | Objetivo; Componentes coletados; Core obrigatório; Plugin BGP; Limitações atuais | 30 |
| docs/adr/0001-netbox-as-single-sot.md | ADR 0001 — NetBox como single source of truth técnico | Status; Contexto; Decisão; Consequências; Referências | 19 |
| docs/adr/0002-n8n-as-orchestrator.md | ADR 0002 — N8N como orquestrador principal | Status; Contexto; Decisão; Consequências; Referências | 19 |
| docs/adr/0003-machine-parseable-naming.md | ADR 0003 — Naming e descrições machine-parseable | Status; Contexto; Decisão; Consequências; Referências | 19 |
| docs/adr/0004-gitops-for-monitoring-assets.md | ADR 0004 — GitOps para ativos de monitoramento | Status; Contexto; Decisão; Consequências; Referências | 20 |
| docs/adr/0005-read-only-equipment-first.md | ADR 0005 — Equipamentos read-only nas fases iniciais | Status; Contexto; Decisão; Consequências; Referências | 19 |
| grafana/README.md | Grafana — Provisionamento e Dashboards | Objetivo; Estrutura; Próximos passos | 14 |
| grafana/dashboards/README.md | Dashboards | - | 10 |
| grafana/dashboards/carrier/README.md | Dashboards — Carrier | - | 3 |
| grafana/dashboards/customer/README.md | Dashboards — Customer | - | 3 |
| grafana/dashboards/infra/README.md | Dashboards — Infra | - | 3 |
| grafana/dashboards/noc/README.md | Dashboards — NOC | - | 3 |
| grafana/dashboards/platform/README.md | Dashboards — Platform | - | 3 |
| n8n/README.md | N8N — Workflows Planejados | Objetivo; Estrutura; Próximos passos | 11 |
| n8n/workflows/wf-compliance-report.md | Workflow — Compliance Report | Objetivo; Trigger; Input esperado; Output esperado; Nodes principais | 40 |
| n8n/workflows/wf-error-handler.md | Workflow — Error Handler | Objetivo; Trigger; Input esperado; Output esperado; Nodes principais | 39 |
| n8n/workflows/wf-netbox-router.md | Workflow — NetBox Router Event | Objetivo; Trigger; Input esperado; Output esperado; Nodes principais (planejado) | 42 |
| n8n/workflows/wf-onboard-circuit.md | Workflow — Onboard Circuit | Objetivo; Trigger; Input esperado; Output esperado; Nodes principais | 39 |
| n8n/workflows/wf-onboard-device.md | Workflow — Onboard Device | Objetivo; Trigger; Input esperado; Output esperado; Nodes principais | 39 |
| n8n/workflows/wf-reconcile.md | Workflow — Reconcile | Objetivo; Trigger; Input esperado; Output esperado; Nodes principais | 41 |
| netbox/README.md | NetBox — Configurações Planejadas | Contexto; Estrutura; Próximos passos | 14 |
| prompts/README.md | Prompts — Guia de uso | Objetivo; Estrutura; Como usar | 18 |
| prompts/approval-workflow-review.md | Approval Workflow Review Prompt | 1. Contexto; 2. Antes de começar; 3. Revisar seção: Safe Create Staged — Base Inventory; 4. Revisar seção: Safe Create Staged — Service Candidates; 5. Revisar seção: Revisão Humana Obrigatória | 250 |
| prompts/architecture-review.md | Prompt — Architecture Review | Checklist; Saída | 18 |
| prompts/code-review.md | Prompt — Code Review Operacional | Instruções; Saída esperada | 25 |
| prompts/docs-updater.md | Prompt — Docs Updater | Checklist; Saída | 16 |
| prompts/first-pilot-run.md | Prompt — First Pilot Run | Objetivo; Instruções; Fluxo de trabalho; Regras importantes | 29 |
| prompts/grafana-dashboard-review.md | Prompt — Grafana Dashboard Review | Checklist | 12 |
| prompts/n8n-workflow-builder.md | Prompt — N8N Workflow Builder | Entradas necessárias; Checklist; Saída | 26 |
| prompts/netbox-data-model-review.md | Prompt — NetBox Data Model Review | Checklist; Saída esperada | 17 |
| prompts/phase-summary.md | Prompt — Phase Summary | Checklist; Saída | 14 |
| prompts/pilot-device-compliance.md | Prompt — Pilot Device Compliance | Objetivo; Referências obrigatórias; Instruções; Fluxo sugerido; Saída esperada | 35 |
| prompts/test-generator.md | Prompt — Test Generator | Checklist; Saída | 17 |
| prompts/zabbix-template-review.md | Prompt — Zabbix Template Review | Checklist | 14 |
| skills/README.md | Skills — Guia de uso | Objetivo; Estrutura; Skills disponíveis | 22 |
| skills/approval-workflow.skill.md | Skill: Approval Workflow | Metadados; Descrição; Quando usar; Entrada esperada; Saída esperada | 271 |
| skills/code-review.skill.md | Skill — Code Review Operacional | Objetivo; Quando usar; Entrada esperada; Saída esperada; Checklist | 46 |
| skills/compliance-report.skill.md | Skill — Compliance Report | Objetivo; Quando usar; Entrada esperada; Saída esperada; Checklist | 33 |
| skills/documentation-maintenance.skill.md | Skill — Documentation Maintenance | Objetivo; Quando usar; Entrada esperada; Saída esperada; Checklist | 32 |
| skills/grafana-dashboard.skill.md | Skill — Grafana Dashboard | Objetivo; Quando usar; Entrada esperada; Saída esperada; Checklist | 36 |
| skills/n8n-workflow.skill.md | Skill — N8N Workflow | Objetivo; Quando usar; Entrada esperada; Saída esperada; Checklist | 40 |
| skills/netbox-modeling.skill.md | Skill — NetBox Modeling | Objetivo; Quando usar; Entrada esperada; Saída esperada; Checklist | 35 |
| skills/pilot-compliance.skill.md | Skill — Pilot Compliance | Objetivo; Quando usar; Entrada esperada; Saída esperada; Checklist | 37 |
| skills/zabbix-template.skill.md | Skill — Zabbix Template | Objetivo; Quando usar; Entrada esperada; Saída esperada; Checklist | 38 |
| zabbix/README.md | Zabbix — Estratégia de Templates e Provisionamento | Objetivo; Estrutura; Próximos passos | 16 |
| zabbix/templates/README.md | Templates | - | 9 |
<!-- AUTO-GENERATED:END -->
