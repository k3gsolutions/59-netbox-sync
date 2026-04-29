"""Response form handlers for local CSV saving."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

def get_responses_dir(reports_root: Path) -> Path:
    """Get week1-responses directory."""
    responses_dir = reports_root / "pilot-device-compliance" / "week1-responses"
    responses_dir.mkdir(parents=True, exist_ok=True)
    return responses_dir

def save_response_csv(
    team: str,
    data: Dict,
    reports_root: Path
) -> Tuple[bool, str]:
    """Save response to CSV file."""
    try:
        responses_dir = get_responses_dir(reports_root)
        csv_file = responses_dir / f"{team}-response.csv"

        # Prepare row
        row = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'team': team,
            'object_key': data.get('object_key', ''),
            'status': data.get('status', ''),
            'tenant': data.get('tenant', ''),
            'service_type': data.get('service_type', ''),
            'criticality': data.get('criticality', ''),
            'owner': data.get('owner', ''),
            'evidence': data.get('evidence', ''),
            'notes': data.get('notes', ''),
            'remote_asn': data.get('remote_asn', ''),
            'remote_bgp_group': data.get('remote_bgp_group', ''),
            'policy_intent': data.get('policy_intent', ''),
            'interface': data.get('interface', ''),
            'vrf': data.get('vrf', ''),
        }

        # Check if file exists
        file_exists = csv_file.exists()

        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            fieldnames = list(row.keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            writer.writerow(row)

        return True, str(csv_file)
    except Exception as e:
        return False, str(e)

def save_response_audit(
    team: str,
    data: Dict,
    reports_root: Path
) -> Tuple[bool, str]:
    """Save response audit JSON."""
    try:
        responses_dir = get_responses_dir(reports_root)
        audit_file = responses_dir / f"{team}-response.audit.json"

        audit_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'team': team,
            'object_key': data.get('object_key', ''),
            'data': {k: v for k, v in data.items() if k not in ['timestamp']},
            'source': 'webui_form'
        }

        # Append to audit log
        entries = []
        if audit_file.exists():
            with open(audit_file, 'r') as f:
                try:
                    entries = json.load(f)
                    if not isinstance(entries, list):
                        entries = [entries]
                except json.JSONDecodeError:
                    entries = []

        entries.append(audit_entry)

        with open(audit_file, 'w') as f:
            json.dump(entries, f, indent=2)

        return True, str(audit_file)
    except Exception as e:
        return False, str(e)

def update_edit_audit_log(
    team: str,
    object_key: str,
    fields_changed: List[str],
    status: str,
    reports_root: Path
) -> Tuple[bool, str]:
    """Update edit audit log."""
    try:
        responses_dir = get_responses_dir(reports_root)
        log_file = responses_dir / "edit-audit-log.md"

        entry = f"""## {datetime.now(timezone.utc).isoformat()}

- Team: {team}
- Object: {object_key}
- Fields Changed: {', '.join(fields_changed)}
- Validation: {status}
- Source: webui_form

"""
        with open(log_file, 'a') as f:
            f.write(entry)

        return True, str(log_file)
    except Exception as e:
        return False, str(e)

def load_response_csv(team: str, reports_root: Path) -> List[Dict]:
    """Load existing responses from CSV."""
    try:
        responses_dir = get_responses_dir(reports_root)
        csv_file = responses_dir / f"{team}-response.csv"

        if not csv_file.exists():
            return []

        rows = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)

        return rows
    except Exception:
        return []

def get_latest_response(team: str, reports_root: Path) -> Optional[Dict]:
    """Get latest response from CSV."""
    rows = load_response_csv(team, reports_root)
    if rows:
        return rows[-1]
    return None
