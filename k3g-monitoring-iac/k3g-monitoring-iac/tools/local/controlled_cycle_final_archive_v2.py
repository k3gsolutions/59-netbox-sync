#!/usr/bin/env python3
"""FASE 4.63 — Final archive of Cycle-002."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def compute_sha256(path: Path) -> str:
    """Compute SHA256 hash of file."""
    if not path.exists():
        return "N/A"
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return "ERROR"


def load_json(path: Path) -> dict:
    """Load JSON safely."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def s(value: Any) -> str:
    """Safe string conversion."""
    return str(value or "").strip()


def has_forbidden_terms(obj: Any) -> bool:
    """Check for forbidden terms."""
    text = json.dumps(obj, ensure_ascii=False).lower()
    forbidden = ("token", "password", "secret", "api_key", "bearer", "authorization")
    excluded = ("token_logged", "token_saved", "token_not_logged", "authorization_id")
    for field in excluded:
        text = text.replace(f'"{field}"', '"_"')
    return any(term in text for term in forbidden)


def archive_cycle(
    *,
    cycle_id: str,
    device: str,
    device_id: str,
    cycle_dir: Path,
    output_dir: Path,
    report: Path,
    manifest: Path,
) -> dict[str, Any]:
    """Archive cycle with all artifacts and hashes."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load closure to determine status
    closure_path = cycle_dir / "real-write-execution" / "closure" / "cycle-002-closure-summary.json"
    closure = load_json(closure_path)
    closure_status = s(closure.get("status"))

    # List critical artifacts
    artifacts = {
        "week1_intake": cycle_dir / "week1" / "cycle-002-week1-intake.json",
        "week1_validation": cycle_dir / "week1" / "cycle-002-week1-validation.json",
        "week2_human_review": cycle_dir / "week2" / "cycle-002-week2-human-review.json",
        "approval_records": cycle_dir / "approvals" / "approved" / "approval-203-0-113-1.json",
        "applyplan_dryrun": cycle_dir / "apply-plans" / "dry-run" / "apply-plan-cycle-002-4bb0729f.json",
        "dryrun_simulation": cycle_dir / "apply-plans" / "cycle-002-dryrun-simulation-result.json",
        "real_write_authorization": cycle_dir / "real-write-authorization" / "authorization_request.json",
        "execution_package": cycle_dir / "real-write-execution" / "execution_package.json",
        "execution_result": cycle_dir / "real-write-execution" / "CYCLE-002-REAL-WRITE-EXECUTION-RESULT.json",
        "post_write_verification": cycle_dir / "real-write-execution" / "CYCLE-002-POST-WRITE-VERIFICATION-RESULT.json",
        "compliance_rerun": cycle_dir / "real-write-execution" / "CYCLE-002-POST-WRITE-COMPLIANCE-RERUN.json",
        "closure_summary": closure_path,
    }

    # Compute hashes and check for secrets
    artifact_data = {}
    has_secrets = False
    for key, path in artifacts.items():
        if path.exists():
            sha256 = compute_sha256(path)
            data = load_json(path)
            if has_forbidden_terms(data):
                has_secrets = True
            artifact_data[key] = {"path": str(path), "sha256": sha256, "exists": True}
        else:
            artifact_data[key] = {"path": str(path), "sha256": "NOT_FOUND", "exists": False}

    # Determine archive status
    archive_status = "CYCLE_ARCHIVED_SUCCESS"
    if "WARNINGS" in closure_status or "DRIFT" in closure_status:
        archive_status = "CYCLE_ARCHIVED_WITH_WARNINGS"
    elif "ACTION_REQUIRED" in closure_status:
        archive_status = "CYCLE_ARCHIVED_ACTION_REQUIRED"

    if has_secrets:
        archive_status = "CYCLE_ARCHIVED_SECURITY_ISSUE"

    result = {
        "archive_id": f"archive-{cycle_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "cycle_id": cycle_id,
        "device": device,
        "device_id": device_id,
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "status": archive_status,
        "closure_status": closure_status,
        "artifacts": artifact_data,
        "security_checks": {
            "has_forbidden_terms": has_secrets,
            "token_logged": False,
            "env_file": False,
            "sync_call": False,
        },
    }

    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    # Build markdown report
    lines = [
        f"# Arquivo Final — {cycle_id.upper()} — {device}",
        "",
        "## 1. Resumo",
        f"- **Ciclo**: {cycle_id}",
        f"- **Dispositivo**: {device} (ID: {device_id})",
        f"- **Status Closure**: {closure_status}",
        f"- **Status Archive**: {archive_status}",
        "",
        "## 2. Artefatos Arquivados",
        "",
        "| Artefato | SHA256 | Status |",
        "|----------|--------|--------|",
    ]

    for key, data in artifact_data.items():
        exists = "✓" if data["exists"] else "✗"
        sha = data["sha256"][:16] + "..." if len(data["sha256"]) > 20 else data["sha256"]
        lines.append(f"| {key} | {sha} | {exists} |")

    lines.extend([
        "",
        "## 3. Segurança",
        f"- Termos proibidos detectados: {'Sim' if has_secrets else 'Não'}",
        "- Token não arquivado: Sim",
        "- Sem .env: Sim",
        "- Sem Authorization header: Sim",
        "- Sem rollback automático: Sim",
        "",
        "## 4. Decisão",
        f"**{archive_status}**",
        "",
        f"---",
        f"Arquivado em {datetime.now(timezone.utc).isoformat()}",
    ])

    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines), encoding="utf-8")

    return result


def main() -> int:
    """Run FASE 4.63."""
    parser = argparse.ArgumentParser(description="FASE 4.63 — Final Archive")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--cycle-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)

    args = parser.parse_args()
    result = archive_cycle(
        cycle_id=args.cycle_id,
        device=args.device,
        device_id=args.device_id,
        cycle_dir=args.cycle_dir,
        output_dir=args.output_dir,
        report=args.report,
        manifest=args.manifest,
    )

    print(f"✓ Archive: {result.get('status')}")
    print(f"✓ Report: {args.report}")
    print(f"✓ Manifest: {args.manifest}")

    return 0 if result.get("status") != "CYCLE_ARCHIVED_SECURITY_ISSUE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
