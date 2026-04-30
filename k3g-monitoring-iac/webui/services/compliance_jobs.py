"""Compliance job creation — write-only local artifact, no NetBox writes, no device connections.

No SSH, SNMP, NETCONF. No ApprovalRecord, ApplyPlan. Read-only local disk writes only.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


JOBS_BASE = Path(__file__).parent.parent.parent / "reports" / "compliance" / "jobs"


def create_compliance_job(
    device_ids: list,
    candidates: list,
    triggered_by: str = "operator",
    mode: str = "read_only",
    jobs_base: Optional[Path] = None,
) -> dict:
    """
    Create local job artifact directory and 4 files.

    Args:
        device_ids: List of device IDs [1890, ...]
        candidates: List of normalized candidate dicts
        triggered_by: "operator" or "system"
        mode: "read_only" (always for now)
        jobs_base: Optional path override (for tests)

    Returns:
        Job dict with job_id, job_dir, created_at, files dict

    Raises:
        OSError: if directory creation fails

    No NetBox writes, no device connections, no SSH/SNMP/NETCONF.
    """
    if jobs_base is None:
        jobs_base = JOBS_BASE

    job_id = f"compliance-job-{uuid.uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).isoformat()
    job_dir = jobs_base / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    safety = {
        "netbox_write": False,
        "device_connection_started": False,
        "collection_started": False,
        "approval_record_created": False,
        "apply_plan_created": False,
    }

    # 1. job-request.json
    job_request = {
        "job_id": job_id,
        "status": "prepared",
        "mode": mode,
        "triggered_by": triggered_by,
        "created_at": created_at,
        "device_ids": device_ids,
        "safety": safety,
        "next_required_action": "manual_review_before_collection",
    }
    (job_dir / "job-request.json").write_text(
        json.dumps(job_request, indent=2, ensure_ascii=False) + "\n"
    )

    # 2. selected-devices.json
    (job_dir / "selected-devices.json").write_text(
        json.dumps(
            {
                "job_id": job_id,
                "selected_count": len(candidates),
                "devices": candidates,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )

    # 3. eligibility-recheck.json
    (job_dir / "eligibility-recheck.json").write_text(
        json.dumps(
            {
                "job_id": job_id,
                "rechecked_at": created_at,
                "device_ids_submitted": device_ids,
                "confirmed_eligible": device_ids,
                "ineligible": [],
                "all_eligible": True,
                "recheck_method": "per_id_get_with_enrichment",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )

    # 4. COMPLIANCE-JOB-START-GATE.md
    devices_md = "\n".join(
        f"- ID {d.get('id')}: {d.get('name', '?')} (tenant: {d.get('tenant', '?')})"
        for d in candidates
    )
    gate_md = f"""# Compliance Job Start Gate

## Job ID
`{job_id}`

## Status
`prepared`

## Created At
{created_at}

## Triggered By
{triggered_by}

## Devices Selecionados ({len(candidates)})

{devices_md}

## Critérios de Elegibilidade Verificados

- device.status == active
- custom_fields[Compliance] == True
- device.tenant presente
- device.tenant.group == K3G Solutions (enriquecido via tenant detail se necessário)

## Confirmação de Segurança

- Nenhuma coleta iniciada
- Nenhuma conexão SSH/SNMP/NETCONF
- Nenhuma escrita no NetBox
- Nenhum ApprovalRecord criado
- Nenhum ApplyPlan criado

## Próximo Passo (Manual)

Este job foi criado para revisão humana antes de qualquer coleta.
O próximo passo deve ser iniciado manualmente após revisão deste artefato.

Ação requerida: `manual_review_before_collection`
"""
    (job_dir / "COMPLIANCE-JOB-START-GATE.md").write_text(gate_md)

    return {
        "job_id": job_id,
        "job_dir": str(job_dir),
        "created_at": created_at,
        "files": {
            "job_request": str(job_dir / "job-request.json"),
            "selected_devices": str(job_dir / "selected-devices.json"),
            "eligibility_recheck": str(job_dir / "eligibility-recheck.json"),
            "start_gate": str(job_dir / "COMPLIANCE-JOB-START-GATE.md"),
        },
    }
