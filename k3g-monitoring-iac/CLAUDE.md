# Claude Project Guide

This repository already uses `AGENTS.md` as the canonical operating guide for Codex and Claude.
This file exists as a Claude-specific entrypoint so the remote host can discover the same project specialties without relying on the global home config alone.

## Read first
1. `PROJECT_CONTEXT.md`
2. `context/CURRENT_STATE.md`
3. `context/NEXT_ACTIONS.md`
4. `AGENTS.md`
5. `docs/13-ai-operating-model.md`

## Specialties
- Code review: `skills/code-review.skill.md`
- Documentation maintenance: `skills/documentation-maintenance.skill.md`
- N8N workflows: `skills/n8n-workflow.skill.md`
- Zabbix templates: `skills/zabbix-template.skill.md`
- Grafana dashboards: `skills/grafana-dashboard.skill.md`
- NetBox modeling: `skills/netbox-modeling.skill.md`
- Compliance reports: `skills/compliance-report.skill.md`

## Reusable prompts
- `prompts/code-review.md`
- `prompts/architecture-review.md`
- `prompts/n8n-workflow-builder.md`
- `prompts/docs-updater.md`
- `prompts/phase-summary.md`
- `prompts/zabbix-template-review.md`
- `prompts/grafana-dashboard-review.md`
- `prompts/netbox-data-model-review.md`
- `prompts/test-generator.md`

## Local tools
- `tools/local/summarize_repo.py`
- `tools/local/update_context_index.py`
- `tools/local/check_docs_links.py`
- `tools/local/generate_phase_report.py`
- other scripts in `tools/local/`

## Sub-agents
- `agents/code-review.md`
- `agents/documentation-maintenance.md`
- `agents/compliance-report.md`
- `agents/netbox-modeling.md`

## Operating constraints
- Keep changes within the current phase.
- Do not call real production APIs without explicit authorization.
- Keep documentation, GitOps, workflows, templates, and tools separated.
- Prefer incremental context updates over wide re-reads.
