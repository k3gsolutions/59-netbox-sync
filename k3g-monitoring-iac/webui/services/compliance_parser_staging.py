"""Parser staging area for SSH collection outputs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .compliance_jobs import JOBS_BASE, load_compliance_job


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _safe_job_dir(job_id: str, jobs_base: Optional[Path] = None) -> Path:
    return (jobs_base or JOBS_BASE) / job_id


def create_parser_staging(job_id: str, jobs_base: Optional[Path] = None) -> dict:
    """Create parser staging manifest and markdown."""
    job = load_compliance_job(job_id, jobs_base)
    job_dir = _safe_job_dir(job_id, jobs_base)
    results_dir = job_dir / "collection-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    manifest = generate_parser_manifest(job_id, jobs_base)
    for device in manifest["devices"]:
        parsed_dir = Path(device["parsed_dir"])
        parsed_dir.mkdir(parents=True, exist_ok=True)
        (parsed_dir / ".gitkeep").touch(exist_ok=True)
    return {
        "job_id": job_id,
        "results_dir": str(results_dir),
        "parser_manifest": manifest,
        "files": {
            "parser_manifest": str(results_dir / "parser-manifest.json"),
            "parser_staging_markdown": str(results_dir / "PARSER-STAGING.md"),
        },
    }


def index_collected_files(job_id: str, jobs_base: Optional[Path] = None) -> list[dict]:
    """Index raw, redacted and parsed files for each device."""
    job = load_compliance_job(job_id, jobs_base)
    job_dir = _safe_job_dir(job_id, jobs_base)
    results_dir = job_dir / "collection-results"
    devices = []

    source_devices = list((job.get("ssh_collection_result") or {}).get("devices") or [])
    if not source_devices:
        source_devices = list((job.get("collection_plan") or {}).get("devices") or [])

    for device in source_devices:
        device_id = str(device.get("device_id") or device.get("id") or "unknown")
        device_dir = results_dir / "devices" / device_id
        raw_dir = device_dir / "raw"
        redacted_dir = device_dir / "redacted"
        parsed_dir = device_dir / "parsed"
        raw_files = sorted(str(path) for path in raw_dir.glob("*") if path.is_file() and path.name != ".gitkeep") if raw_dir.exists() else []
        redacted_files = sorted(str(path) for path in redacted_dir.glob("*") if path.is_file() and path.name != ".gitkeep") if redacted_dir.exists() else []
        parsed_files = sorted(str(path) for path in parsed_dir.glob("*") if path.is_file() and path.name != ".gitkeep") if parsed_dir.exists() else []
        devices.append(
            {
                "device_id": device.get("device_id"),
                "name": device.get("name"),
                "profile": (device.get("collection_profile") or {}).get("profile_id") or device.get("profile_id") or "default-readonly",
                "raw_files": raw_files,
                "redacted_files": redacted_files,
                "parsed_files": parsed_files,
                "parsed_dir": str(parsed_dir),
                "ready_for_parsing": bool(redacted_files),
            }
        )

    return devices


def generate_parser_manifest(job_id: str, jobs_base: Optional[Path] = None) -> dict:
    """Generate parser manifest JSON and markdown."""
    job_dir = _safe_job_dir(job_id, jobs_base)
    results_dir = job_dir / "collection-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    devices = index_collected_files(job_id, jobs_base)
    manifest = {
        "job_id": job_id,
        "generated_at": _now(),
        "devices": devices,
        "safety": {
            "raw_not_displayed_in_ui": True,
            "redaction_available": True,
            "netbox_write": False,
        },
    }
    manifest_path = results_dir / "parser-manifest.json"
    markdown_path = results_dir / "PARSER-STAGING.md"
    _dump_json(manifest_path, manifest)

    lines = [
        "# PARSER-STAGING",
        "",
        f"## Job ID\n`{job_id}`",
        "",
        "## Devices",
    ]
    if not devices:
        lines.append("- none")
    for device in devices:
        lines.extend(
            [
                "",
                f"### {device.get('name')}",
                f"- device_id: {device.get('device_id')}",
                f"- profile: {device.get('profile')}",
                f"- ready_for_parsing: {device.get('ready_for_parsing')}",
                f"- raw_files: {len(device.get('raw_files') or [])}",
                f"- redacted_files: {len(device.get('redacted_files') or [])}",
                f"- parsed_files: {len(device.get('parsed_files') or [])}",
            ]
        )
    lines.extend(
        [
            "",
            "## Safety",
            "- raw_not_displayed_in_ui=true",
            "- redaction_available=true",
            "- netbox_write=false",
        ]
    )
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest
