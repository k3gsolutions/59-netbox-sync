#!/usr/bin/env python3
"""FASE 4.75 — Cycle-003 Week 2 Preparation."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict:
	"""Load JSON safely."""
	try:
		return json.loads(path.read_text(encoding="utf-8"))
	except Exception:
		return {}


def prepare_week2(
	*,
	cycle_id: str,
	device: str,
	device_id: str,
	cycle_dir: Path,
	week1_validation: Path,
	output_dir: Path,
) -> dict[str, Any]:
	"""Prepare Week 2 structure."""
	output_dir.mkdir(parents=True, exist_ok=True)
	(output_dir / "approval-drafts").mkdir(exist_ok=True)
	(output_dir / "audit").mkdir(exist_ok=True)

	# Load Week 1 validation
	validation = load_json(week1_validation)
	decision = validation.get("decision", "")
	files_validated = validation.get("files_validated", 0)

	issues = []

	# Check Week 1 validation passed
	if "VALIDATION_BLOCKED" in decision:
		issues.append("week1 validation blocked")
	elif "VALIDATION_PASSED" not in decision:
		issues.append(f"unexpected week1 decision: {decision}")

	if files_validated == 0:
		issues.append("no files validated in week1")

	# Determine decision
	if issues:
		if files_validated > 0:
			status_decision = "WEEK2_PREPARATION_READY_WITH_RESTRICTIONS"
			status_reason = f"Week 1 partial: {', '.join(issues)}"
		else:
			status_decision = "WEEK2_PREPARATION_BLOCKED"
			status_reason = "Week 1 validation failed; no items ready"
	else:
		status_decision = "WEEK2_PREPARATION_READY"
		status_reason = f"Week 1 passed; {files_validated} file(s) validated"

	# Create plan
	plan_file = output_dir / f"{cycle_id.upper()}-WEEK2-PLAN.md"
	plan_text = f"""# Week 2 Plan — {cycle_id.upper()}

## Objetivo
Revisar e aprovar respostas validadas da Week 1 para Cycle-003.

## Etapas
1. Review Board: montar painel de revisão humana
2. Decisões: coletar decisões humanas (approve/reject/defer/block)
3. Proposed Records: promover aprovados para ApprovalRecords propostos
4. Approval Readiness: validar prontos para revisão manual

## Responsáveis
- Technical Lead: revisão técnica
- Operations Lead: revisão operacional
- Security Lead: validação de segurança

## Formato de Decisão
- **approve_for_approval_record**: criar ApprovalRecord proposed
- **request_changes**: requerer alterações antes de approved
- **rejected**: rejeitar completamente
- **deferred**: postergar para próximo ciclo
- **blocked**: bloquear por motivo técnico/segurança

## Próximo Passo
Week 2 Human Review

---
Criado em {datetime.now(timezone.utc).isoformat()}
"""
	plan_file.write_text(plan_text, encoding="utf-8")

	# Create review board
	board_file = output_dir / f"{cycle_id.upper()}-WEEK2-REVIEW-BOARD.md"
	board_text = f"""# Week 2 Review Board — {cycle_id.upper()}

## Membros
- Reviewer 1: Technical Lead
- Reviewer 2: Operations Lead
- Reviewer 3: Security Lead (optional)

## Itens para Revisão
Total: {files_validated} item(s) validado(s) na Week 1

## Status
BOARD_READY

---
Criado em {datetime.now(timezone.utc).isoformat()}
"""
	board_file.write_text(board_text, encoding="utf-8")

	# Create decisions CSV template
	decisions_file = output_dir / f"{cycle_id.upper()}-WEEK2-DECISIONS.csv"
	with open(decisions_file, "w", newline="", encoding="utf-8") as f:
		writer = csv.writer(f)
		writer.writerow([
			"item_id",
			"device",
			"decision",
			"reviewed_by",
			"reviewed_at",
			"approval_record_allowed",
			"reason",
			"notes"
		])
		# Write one row as template
		writer.writerow([
			"1",
			device,
			"pending_review",
			"",
			"",
			"false",
			"",
			"Awaiting human review"
		])

	# Create status template
	status_file = output_dir / f"{cycle_id.upper()}-WEEK2-STATUS.md"
	status_text = f"""# Week 2 Status — {cycle_id.upper()}

- **Ciclo**: {cycle_id}
- **Dispositivo**: {device}
- **Período**: Week 2
- **Status**: PREPARADO
- **Data**: {datetime.now(timezone.utc).isoformat()}

## Resumo
- Files validated: {files_validated}
- Review Board: ready
- Decisions CSV: template created
- Approval Drafts: ready

## Próximos Passos
1. Revisor preenche CYCLE-003-WEEK2-DECISIONS.csv
2. Executar Week 2 Human Review
3. Promover aprovados para ApprovalRecords
4. Approval readiness gate

---
"""
	status_file.write_text(status_text, encoding="utf-8")

	result = {
		"preparation_id": f"week2-prep-{cycle_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
		"cycle_id": cycle_id,
		"device": device,
		"device_id": device_id,
		"prepared_at": datetime.now(timezone.utc).isoformat(),
		"decision": status_decision,
		"reason": status_reason,
		"files_validated": files_validated,
		"files_created": {
			"plan": str(plan_file),
			"review_board": str(board_file),
			"decisions_csv": str(decisions_file),
			"status": str(status_file),
			"approval_drafts_dir": str(output_dir / "approval-drafts"),
			"audit_dir": str(output_dir / "audit"),
		},
	}

	output_dir.parent / f"cycle-003-week2-preparation.json"
	return result


def main() -> int:
	"""Run FASE 4.75."""
	parser = argparse.ArgumentParser(description="FASE 4.75 — Week 2 Preparation")
	parser.add_argument("--cycle-id", required=True)
	parser.add_argument("--device", required=True)
	parser.add_argument("--device-id", required=True)
	parser.add_argument("--cycle-dir", type=Path, required=True)
	parser.add_argument("--week1-validation", type=Path, required=True)
	parser.add_argument("--output-dir", type=Path, required=True)

	args = parser.parse_args()
	result = prepare_week2(
		cycle_id=args.cycle_id,
		device=args.device,
		device_id=args.device_id,
		cycle_dir=args.cycle_dir,
		week1_validation=args.week1_validation,
		output_dir=args.output_dir,
	)

	print(f"✓ Week 2 prepared: {result.get('decision')}")
	print(f"✓ Decisions CSV: {result['files_created']['decisions_csv']}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
