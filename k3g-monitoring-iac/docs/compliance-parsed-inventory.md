# Parsed Inventory Artifact

## Goal

Store parser output in a structured local artifact that can be reviewed without exposing raw SSH output.

## Per-device schema

- `device_id`
- `name`
- `profile`
- `parsed_at`
- `parser`
- `summary`
- `system`
- `interfaces`
- `ipv4_interfaces`
- `ipv6_interfaces`
- `bgp_peers`
- `route_policies`
- `ip_prefixes`
- `ipv6_prefixes`
- `snmp`
- `warnings`
- `skipped`

## Review surface

- review `PARSED-INVENTORY.md`
- review `PARSER-RESULT.md`
- use `/reports/download` for `.md` and `.json` artifacts

## Safety

- raw output remains hidden in the UI
- parsed artifacts are local-only
- no NetBox write
- no device connection
