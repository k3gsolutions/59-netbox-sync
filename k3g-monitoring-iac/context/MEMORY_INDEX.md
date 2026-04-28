# Memory Index
Gerado em: 2026-04-28 10:32:26 UTC
## Arquivos de contexto
| Arquivo | Finalidade provável |
| --- | --- |
| README.md | Visão geral do projeto |
| PROJECT_CONTEXT.md | Contexto rápido para agentes/IA |
| ROADMAP.md | Planejamento faseado |
| PHASE0_BASELINE.md | Checklist operacional da fase |
| AGENTS.md | Regras de atuação para agentes de IA |
| context/CURRENT_STATE.md | Current State — FASE 1.5 (Complete) |
| context/GLOSSARY.md | GLOSSARY |
| context/NEXT_ACTIONS.md | Next Actions — Roadmap |
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
<!-- AUTO-GENERATED:END -->
