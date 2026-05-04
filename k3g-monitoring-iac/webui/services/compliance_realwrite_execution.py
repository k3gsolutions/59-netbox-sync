"""
Compliance Real Write Execution Full Cycle (FASES COMPLIANCE-REALWRITE-001–010)

Authorization → Preflight → Execution → Verification → Closure
Token environment-only, one-shot execution, fail-fast.
"""

import json
import hashlib
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple


def load_dryrun_execution_validation(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load dry-run execution validation."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    validation_file = jobs_base / job_id / "applyplan" / "dry-run" / "dry-run-execution-validation.json"
    if not validation_file.exists():
        return {}

    with open(validation_file, "r") as f:
        return json.load(f)


def load_dryrun_applyplan(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load dry-run ApplyPlan."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    dryrun_file = jobs_base / job_id / "applyplan" / "dry-run" / "dry-run-applyplan.json"
    if not dryrun_file.exists():
        return {}

    with open(dryrun_file, "r") as f:
        return json.load(f)


def evaluate_realwrite_readiness_gate(job_id: str, operator: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """REALWRITE-001: Evaluate real-write readiness."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    # Check dry-run validation
    validation = load_dryrun_execution_validation(job_id, jobs_base)
    if not validation:
        raise ValueError("Dry-run execution validation not found")

    if validation.get("decision") != "DRY_RUN_VALIDATION_PASSED":
        raise ValueError(f"Dry-run validation status: {validation.get('decision')}; must be PASSED")

    # Create directory
    realwrite_dir = jobs_base / job_id / "real-write"
    realwrite_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "job_id": job_id,
        "status": "gate_evaluated",
        "decision": "REAL_WRITE_READINESS_READY",
        "evaluated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "evaluated_by": operator,
        "dry_run_validation": validation.get("decision"),
        "safety": {
            "netbox_write": False,
            "token_in_memory_only": True,
            "one_shot_execution": True,
            "no_retry": True,
            "no_rollback_automatic": True
        }
    }

    # Write gate
    gate_file = realwrite_dir / "real-write-readiness-gate.json"
    with open(gate_file, "w") as f:
        json.dump(result, f, indent=2)

    return result


def build_realwrite_authorization_package(job_id: str, operator: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """REALWRITE-002: Build authorization package with required phrase."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    # Load ApplyPlan
    applyplan = load_dryrun_applyplan(job_id, jobs_base)
    if not applyplan:
        raise ValueError("Dry-run ApplyPlan not found")

    # Create authorization ID
    auth_id = hashlib.sha256(f"{job_id}-{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:8].upper()

    # Generate required phrase
    required_phrase = f"AUTORIZO_PRE_FLIGHT_ESCRITA_REAL_{job_id}_{auth_id}"

    # Create directory
    auth_dir = jobs_base / job_id / "real-write" / "authorization"
    auth_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "authorization_id": auth_id,
        "job_id": job_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "created_by": operator,
        "required_phrase": required_phrase,
        "item_count": len(applyplan.get("items", [])),
        "safety": {
            "no_write_executed": True,
            "no_token_read": True,
            "no_network_call": True,
            "final_preflight_required": True,
            "explicit_operator_authorization_required": True
        }
    }

    # Write package
    auth_file = auth_dir / "authorization-request.json"
    with open(auth_file, "w") as f:
        json.dump(result, f, indent=2)

    # Write markdown
    md_content = _generate_authorization_markdown(result)
    md_file = auth_dir / "REAL-WRITE-AUTHORIZATION-PACKAGE.md"
    with open(md_file, "w") as f:
        f.write(md_content)

    return result


def _generate_authorization_markdown(result: Dict[str, Any]) -> str:
    """Generate authorization package markdown."""
    lines = [
        "# Real-Write Authorization Package",
        "",
        f"**Authorization ID:** {result.get('authorization_id')}",
        f"**Job ID:** {result.get('job_id')}",
        f"**Created at:** {result.get('created_at')}",
        f"**Created by:** {result.get('created_by')}",
        "",
        "## Required Authorization Phrase",
        "",
        f"```",
        f"{result.get('required_phrase')}",
        f"```",
        "",
        "## Instructions",
        "",
        "1. Operator must copy the required phrase EXACTLY",
        "2. Pass phrase to Final Preflight Gate",
        "3. No modifications to phrase allowed (case-sensitive)",
        "",
        "## Safety",
        "",
        "✗ No NetBox writes at this stage",
        "✗ No tokens used",
        "✗ Final preflight required",
        "",
    ]

    return "\n".join(lines)


def validate_realwrite_authorization(
    job_id: str, operator: str, authorization_phrase: str, jobs_base: Optional[Path] = None
) -> Dict[str, Any]:
    """REALWRITE-003: Final Preflight Gate — validate authorization phrase."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    # Load authorization package
    auth_dir = jobs_base / job_id / "real-write" / "authorization"
    auth_file = auth_dir / "authorization-request.json"
    if not auth_file.exists():
        raise ValueError("Authorization package not found")

    with open(auth_file, "r") as f:
        auth_package = json.load(f)

    # Validate phrase
    required_phrase = auth_package.get("required_phrase")
    if authorization_phrase != required_phrase:
        raise ValueError("Authorization phrase does not match")

    # Create directory
    preflight_dir = auth_dir
    preflight_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "job_id": job_id,
        "status": "preflight_cleared",
        "decision": "FINAL_PREFLIGHT_READY",
        "validated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "validated_by": operator,
        "authorization_id": auth_package.get("authorization_id"),
        "safety": {
            "netbox_write": False,
            "token_in_memory_only": True,
            "one_shot_execution": True
        }
    }

    # Write preflight
    preflight_file = preflight_dir / "final-preflight-gate.json"
    with open(preflight_file, "w") as f:
        json.dump(result, f, indent=2)

    return result


def build_realwrite_execution_package(job_id: str, operator: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """REALWRITE-004: Build execution package (execution_allowed locked to false)."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    # Load ApplyPlan
    applyplan = load_dryrun_applyplan(job_id, jobs_base)
    if not applyplan:
        raise ValueError("Dry-run ApplyPlan not found")

    # Load preflight
    preflight_file = jobs_base / job_id / "real-write" / "authorization" / "final-preflight-gate.json"
    if not preflight_file.exists():
        raise ValueError("Final preflight gate not found")

    with open(preflight_file, "r") as f:
        preflight = json.load(f)

    if preflight.get("decision") != "FINAL_PREFLIGHT_READY":
        raise ValueError(f"Preflight decision: {preflight.get('decision')}; must be READY")

    # Create execution ID
    exec_id = hashlib.sha256(f"{job_id}-{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:8].upper()

    # Generate execution phrase
    execution_phrase = f"EXECUTAR_ESCRITA_REAL_{job_id}_{exec_id}"

    # Create directory
    execution_dir = jobs_base / job_id / "real-write" / "execution"
    execution_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "execution_package_id": exec_id,
        "job_id": job_id,
        "status": "prepared",
        "mode": "real_write_prepared",
        "execution_allowed": False,  # SAFETY LOCK
        "token_required_in_next_phase": True,
        "explicit_confirm_required": True,
        "one_shot_execution": True,
        "required_execution_phrase": execution_phrase,
        "items": applyplan.get("items", []),
        "item_count": len(applyplan.get("items", [])),
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "created_by": operator,
        "safety": {
            "execution_allowed": False,
            "token_in_memory_only": True,
            "no_retry": True,
            "no_rollback_automatic": True,
            "requires_netbox_write_token": True
        }
    }

    # Write execution package
    exec_file = execution_dir / "execution-package.json"
    with open(exec_file, "w") as f:
        json.dump(result, f, indent=2)

    # Write markdown
    md_content = _generate_execution_package_markdown(result)
    md_file = execution_dir / "REAL-WRITE-EXECUTION-PACKAGE.md"
    with open(md_file, "w") as f:
        f.write(md_content)

    return result


def _generate_execution_package_markdown(result: Dict[str, Any]) -> str:
    """Generate execution package markdown."""
    lines = [
        "# Real-Write Execution Package",
        "",
        f"**Execution ID:** {result.get('execution_package_id')}",
        f"**Job ID:** {result.get('job_id')}",
        f"**Status:** {result.get('status')}",
        f"**Mode:** {result.get('mode')}",
        f"**Execution Allowed:** {result.get('execution_allowed')}",
        "",
        "## Required Execution Phrase",
        "",
        f"```",
        f"{result.get('required_execution_phrase')}",
        f"```",
        "",
        "## Pre-Execution Checklist",
        "",
        "- [ ] Operator has NETBOX_WRITE_TOKEN in environment",
        "- [ ] Token is NOT printed or logged anywhere",
        "- [ ] Execution phrase copied exactly",
        "- [ ] Ready for one-shot execution",
        "",
        "## Safety",
        "",
        "✗ execution_allowed=false (locked)",
        "✗ No retry on failure",
        "✗ No automatic rollback",
        "✓ One-shot execution only",
        "",
    ]

    return "\n".join(lines)


def validate_realwrite_execution_package(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """REALWRITE-005: Validate execution package structure and safety locks."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    # Load execution package
    exec_dir = jobs_base / job_id / "real-write" / "execution"
    exec_file = exec_dir / "execution-package.json"
    if not exec_file.exists():
        raise ValueError("Execution package not found")

    with open(exec_file, "r") as f:
        exec_package = json.load(f)

    # Validate safety locks
    issues = []

    if exec_package.get("execution_allowed") is not False:
        issues.append("execution_allowed must be False")

    if exec_package.get("token_required_in_next_phase") is not True:
        issues.append("token_required_in_next_phase must be True")

    if exec_package.get("one_shot_execution") is not True:
        issues.append("one_shot_execution must be True")

    safety = exec_package.get("safety", {})
    if safety.get("execution_allowed") is not False:
        issues.append("safety.execution_allowed must be False")

    if safety.get("no_retry") is not True:
        issues.append("safety.no_retry must be True")

    if safety.get("no_rollback_automatic") is not True:
        issues.append("safety.no_rollback_automatic must be True")

    # Determine decision
    decision = "EXECUTION_PACKAGE_INVALID" if issues else "EXECUTION_PACKAGE_VALID"

    result = {
        "job_id": job_id,
        "status": "validation_completed",
        "decision": decision,
        "validated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "issues": issues,
        "issue_count": len(issues),
        "safety": {
            "netbox_write": False,
            "token_not_required": True,
            "validation_only": True
        }
    }

    # Write validation
    validation_file = exec_dir / "execution-package-validation.json"
    with open(validation_file, "w") as f:
        json.dump(result, f, indent=2)

    return result


def evaluate_realwrite_freeze(job_id: str, operator: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """REALWRITE-006: Final no-write freeze before execution."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    # Load execution package validation
    validation_file = jobs_base / job_id / "real-write" / "execution" / "execution-package-validation.json"
    if not validation_file.exists():
        raise ValueError("Execution package validation not found")

    with open(validation_file, "r") as f:
        validation = json.load(f)

    if validation.get("decision") != "EXECUTION_PACKAGE_VALID":
        raise ValueError(f"Execution package validation: {validation.get('decision')}; must be VALID")

    result = {
        "job_id": job_id,
        "status": "freeze_evaluated",
        "decision": "READY_FOR_REAL_WRITE_PHASE",
        "evaluated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "evaluated_by": operator,
        "final_check": "No more gates until execution token is provided",
        "safety": {
            "netbox_write": False,
            "token_still_not_required": True
        }
    }

    # Write freeze
    freeze_file = jobs_base / job_id / "real-write" / "execution" / "final-no-write-freeze.json"
    with open(freeze_file, "w") as f:
        json.dump(result, f, indent=2)

    return result


def load_realwrite_execution_result(job_id: str, jobs_base: Optional[Path] = None) -> Dict[str, Any]:
    """Load real-write execution result (created by CLI tool)."""
    if jobs_base is None:
        jobs_base = Path("reports/compliance/jobs")

    result_file = jobs_base / job_id / "real-write" / "execution" / "real-write-execution-result.json"
    if not result_file.exists():
        return {}

    with open(result_file, "r") as f:
        return json.load(f)
