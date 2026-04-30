#!/usr/bin/env python3
"""FASE 4.26 — Controlled Operation Cycle Final Archive.

Archive Cycle-001 with SHA256 hashes and security validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of file."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception:
        return ""


def check_for_secrets(file_path: Path) -> list[str]:
    """Check file for secret keywords."""
    secrets_found = []
    blocked_keywords = [
        "NETBOX_WRITE_TOKEN",
        "Authorization: Token",
        "token",
        "password",
        "secret",
        "api_key",
        "bearer",
        "authorization",
        ".env",
        "payload.local",
    ]

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            for keyword in blocked_keywords:
                if keyword.lower() in content.lower():
                    secrets_found.append(keyword)
    except Exception:
        pass

    return secrets_found


def index_cycle_artifacts(cycle_dir: Path) -> Dict[str, Any]:
    """Index all artifacts in cycle directory."""
    artifacts = {}
    artifact_count = 0

    for file_path in cycle_dir.rglob("*.json"):
        if "raw" in str(file_path) or ".env" in str(file_path):
            continue

        rel_path = file_path.relative_to(cycle_dir)
        sha256 = calculate_sha256(file_path)
        secrets = check_for_secrets(file_path)

        artifacts[str(rel_path)] = {
            "path": str(rel_path),
            "sha256": sha256,
            "size_bytes": file_path.stat().st_size,
            "secrets_found": secrets,
        }
        artifact_count += 1

    for file_path in cycle_dir.rglob("*.md"):
        rel_path = file_path.relative_to(cycle_dir)
        sha256 = calculate_sha256(file_path)
        secrets = check_for_secrets(file_path)

        artifacts[str(rel_path)] = {
            "path": str(rel_path),
            "sha256": sha256,
            "size_bytes": file_path.stat().st_size,
            "secrets_found": secrets,
        }
        artifact_count += 1

    return artifacts


def main() -> int:
    """Run FASE 4.26."""
    parser = argparse.ArgumentParser(description="FASE 4.26 — Final Archive")
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--cycle-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)

    args = parser.parse_args()

    # Index artifacts
    if not args.cycle_dir.exists():
        print(f"✗ Cycle directory not found: {args.cycle_dir}")
        return 1

    artifacts = index_cycle_artifacts(args.cycle_dir)

    # Check for secrets
    secrets_found_count = sum(
        len(a.get("secrets_found", [])) for a in artifacts.values()
    )

    # Determine status
    if secrets_found_count > 0:
        status = "CYCLE_ARCHIVED_ACTION_REQUIRED"
    else:
        status = "CYCLE_ARCHIVED_SUCCESS"

    # Build manifest
    manifest = {
        "cycle_id": args.cycle_id,
        "device": args.device,
        "device_id": args.device_id,
        "status": status,
        "archived_at": datetime.utcnow().isoformat() + "+00:00",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "secrets_found_count": secrets_found_count,
        "archive_complete": True,
    }

    # Write manifest
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with open(args.manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Generate report
    markdown = f"""# Archive Final — {args.cycle_id} — {args.device}

## 1. Resumo
- Cycle: {args.cycle_id}
- Device: {args.device}
- Device ID: {args.device_id}
- Status: {status}
- Artefatos: {len(artifacts)}
- Segredos encontrados: {secrets_found_count}

## 2. Artefatos Arquivados
"""

    for artifact_name, artifact_info in artifacts.items():
        markdown += f"""
### {artifact_name}
- SHA256: {artifact_info.get('sha256', 'N/A')[:16]}...
- Tamanho: {artifact_info.get('size_bytes', 0)} bytes
"""
        if artifact_info.get('secrets_found'):
            markdown += f"- Segredos: {', '.join(artifact_info.get('secrets_found', []))}\n"

    markdown += """

## 3. Segurança
"""

    if secrets_found_count > 0:
        markdown += f"✗ {secrets_found_count} segredos encontrados\n"
    else:
        markdown += "✓ Sem segredos\n"

    markdown += """
## 4. Decisão
"""

    if status == "CYCLE_ARCHIVED_SUCCESS":
        markdown += "✓ CYCLE_ARCHIVED_SUCCESS — Sem segredos. Archive completo.\n"
    else:
        markdown += "✗ CYCLE_ARCHIVED_ACTION_REQUIRED — Segredos detectados.\n"

    markdown += f"""

---
Archived at {manifest['archived_at']}
"""

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(markdown, encoding="utf-8")

    print(f"✓ Archive complete: {status}")
    print(f"✓ Artifacts: {len(artifacts)}")
    print(f"✓ Secrets found: {secrets_found_count}")
    print(f"✓ Manifest: {args.manifest}")

    return 0 if status == "CYCLE_ARCHIVED_SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
