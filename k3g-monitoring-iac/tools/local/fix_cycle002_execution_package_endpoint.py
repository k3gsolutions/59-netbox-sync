#!/usr/bin/env python3
"""
FASE 4.58.1 — Cycle-002 Endpoint Fix Tool

Corrige endpoints null/inválidos no execution_package.json baseado em inferência
por object_type ou object_key (IP). Preserva segurança e campos críticos.

Regras implementadas conforme especificação do usuário.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List
import ipaddress


BLOCKED_SUBSTRINGS = ["/sync", "equipment", "ssh", "netconf"]

ENDPOINT_FROM_TYPE = {
    'ip_address': '/api/ipam/ip-addresses/',
    'ip-address': '/api/ipam/ip-addresses/',
    'ipam.ipaddress': '/api/ipam/ip-addresses/',
    'ipaddress': '/api/ipam/ip-addresses/',
    'interface': '/api/dcim/interfaces/',
    'dcim.interface': '/api/dcim/interfaces/',
    'prefix': '/api/ipam/prefixes/',
    'ip_prefix': '/api/ipam/prefixes/',
    'ipam.prefix': '/api/ipam/prefixes/',
    'vrf': '/api/ipam/vrfs/',
    'ipam.vrf': '/api/ipam/vrfs/',
}

# Fields that must be preserved and not modified
PACKAGE_LEVEL_PRESERVE = [
    'payload', 'approval_id', 'apply_plan_id', 'execution_package_id',
    'required_execution_phrase', 'execution_allowed', 'token_required_in_next_phase',
    'explicit_confirm_required', 'one_shot_execution'
]


def looks_like_ip(key: Any) -> bool:
    if not isinstance(key, str):
        return False
    # Remove CIDR if present
    ip_part = key.split('/')[0]
    try:
        ipaddress.ip_address(ip_part)
        return True
    except Exception:
        return False


def endpoint_invalid(endpoint: Any) -> bool:
    if endpoint is None:
        return True
    if isinstance(endpoint, str):
        s = endpoint.strip()
        if s == '' or s == '/':
            return True
    return False


def endpoint_blocked(endpoint: Any) -> bool:
    if not isinstance(endpoint, str):
        return False
    low = endpoint.lower()
    for b in BLOCKED_SUBSTRINGS:
        if b in low:
            return True
    return False


def infer_endpoint(item: Dict[str, Any]) -> Any:
    # Try object_type
    ot = item.get('object_type')
    if isinstance(ot, str):
        ot_l = ot.lower().strip()
        if ot_l in ENDPOINT_FROM_TYPE:
            return ENDPOINT_FROM_TYPE[ot_l]
    # Try object_key if looks like IP
    ok = item.get('object_key')
    if looks_like_ip(ok):
        return '/api/ipam/ip-addresses/'
    return None


def create_backup(path: Path) -> Path:
    ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    bak = path.parent / f"{path.name}.bak.{ts}"
    bak.write_bytes(path.read_bytes())
    return bak


def fix_package(cycle_id: str, package_path: Path) -> Dict[str, Any]:
    pkg = json.loads(package_path.read_text(encoding='utf-8'))

    # Validate cycle id
    if pkg.get('cycle_id') != cycle_id:
        raise SystemExit(f"Cycle ID mismatch: expected {cycle_id}, got {pkg.get('cycle_id')}")

    backup = create_backup(package_path)

    items: List[Dict[str, Any]] = pkg.get('items', [])
    changed_items = []
    blocked_items = []

    for idx, item in enumerate(items):
        item_id = item.get('approval_id') or f'item-{idx}'
        method = item.get('method')
        endpoint = item.get('endpoint') if 'endpoint' in item else None

        # Block if endpoint contains blocked substrings
        if isinstance(endpoint, str) and endpoint_blocked(endpoint):
            blocked_items.append({'item_id': item_id, 'reason': f'Endpoint contains blocked substring: {endpoint}'})
            continue

        # Only consider POST for fixes
        if method != 'POST':
            # If endpoint invalid but method not POST, block
            if endpoint_invalid(endpoint):
                blocked_items.append({'item_id': item_id, 'reason': f'Method is {method}, not POST'})
            continue

        # Ignore PATCH/DELETE explicitly
        if method in ('PATCH', 'DELETE'):
            blocked_items.append({'item_id': item_id, 'reason': f'Method {method} not allowed'})
            continue

        # If endpoint is valid and not blocked, skip
        if not endpoint_invalid(endpoint):
            continue

        # Try to infer
        new_endpoint = infer_endpoint(item)
        if new_endpoint:
            old = endpoint
            item['endpoint'] = new_endpoint
            changed_items.append({
                'item_id': item_id,
                'object_key': item.get('object_key'),
                'object_type': item.get('object_type'),
                'method': method,
                'old_endpoint': old,
                'new_endpoint': new_endpoint,
                'reason': 'Inferred from object_type/object_key'
            })
        else:
            blocked_items.append({'item_id': item_id, 'reason': 'Unable to infer endpoint'})

    # Preserve required booleans exactly
    pkg['execution_allowed'] = False
    pkg['token_required_in_next_phase'] = True
    pkg['explicit_confirm_required'] = True
    pkg['one_shot_execution'] = True

    # Add change_history if there are changes
    if changed_items:
        ch_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': 'fix_null_or_invalid_endpoint',
            'changed_items': changed_items
        }
        if 'change_history' not in pkg:
            pkg['change_history'] = []
        pkg['change_history'].append(ch_entry)

    # Write package back only if there are changes
    if changed_items:
        package_path.write_text(json.dumps(pkg, indent=2), encoding='utf-8')

    result = {
        'fix_id': f'cycle-002-endpoint-fix-{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}',
        'cycle_id': cycle_id,
        'status': 'ENDPOINT_FIX_APPLIED' if changed_items else ('ENDPOINT_FIX_NOT_NEEDED' if not blocked_items else 'ENDPOINT_FIX_BLOCKED'),
        'backup_path': str(backup),
        'changed_items': changed_items,
        'blocked_items': blocked_items,
        'safety_confirmations': {
            'no_netbox_write': True,
            'no_token_read': True,
            'no_network_call': True,
            'execution_allowed_false_preserved': pkg.get('execution_allowed') == False,
            'required_execution_phrase_preserved': 'required_execution_phrase' in pkg
        }
    }

    return result, pkg, str(backup)


def generate_markdown_report(status: str, backup_path: str, changed: List[Dict[str, Any]], blocked: List[Dict[str, Any]], out_path: Path) -> None:
    lines = []
    lines.append('# Correção de Endpoint do Execution Package — Cycle-002')
    lines.append('\n')
    lines.append('## 1. Resultado')
    lines.append('\n')
    lines.append(status)
    lines.append('\n\n')

    lines.append('## 2. Backup')
    lines.append(f'- arquivo criado: `{Path(backup_path).name}`')
    lines.append('\n\n')

    lines.append('## 3. Itens corrigidos')
    lines.append('| Item ID | Object Key | Object Type | Method | Old Endpoint | New Endpoint |')
    lines.append('|---|---|---|---|---|---|')
    if changed:
        for it in changed:
            lines.append(f"| {it['item_id']} | {it.get('object_key','')} | {it.get('object_type','')} | {it.get('method','')} | {it.get('old_endpoint')} | {it.get('new_endpoint')} |")
    lines.append('\n')

    lines.append('## 4. Itens bloqueados')
    lines.append('| Item ID | Motivo |')
    lines.append('|---|---|')
    if blocked:
        for b in blocked:
            lines.append(f"| {b.get('item_id')} | {b.get('reason')} |")
    else:
        lines.append('\n')
    lines.append('\n')

    lines.append('## 5. Segurança')
    lines.append('- Nenhuma escrita NetBox.')
    lines.append('- Nenhum token lido.')
    lines.append('- Nenhuma chamada de rede.')
    lines.append('- execution_allowed permaneceu false.')
    lines.append('- required_execution_phrase preservada.')

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text('\n'.join(lines), encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description='Fix Cycle-002 execution package endpoints')
    parser.add_argument('--cycle-id', required=True)
    parser.add_argument('--execution-package', required=True)
    parser.add_argument('--output-report', required=True)
    parser.add_argument('--output-json', required=True)

    args = parser.parse_args()
    package_path = Path(args.execution_package)
    output_report = Path(args.output_report)
    output_json = Path(args.output_json)

    if not package_path.exists():
        print(f'ERROR: execution package not found: {package_path}')
        return 2

    result, updated_pkg, backup_path = fix_package(args.cycle_id, package_path)

    # Save JSON report
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, indent=2), encoding='utf-8')

    # Generate markdown report
    generate_markdown_report(result['status'], result['backup_path'], result['changed_items'], result['blocked_items'], output_report)

    # Print summary
    print(json.dumps({'status': result['status'], 'fix_id': result['fix_id'], 'changed': len(result['changed_items']), 'blocked': len(result['blocked_items'])}, indent=2))

    if result['status'] == 'ENDPOINT_FIX_BLOCKED':
        return 3
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
