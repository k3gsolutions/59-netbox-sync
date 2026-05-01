# Compliance Policy Compare (FASES COMPARE-001–002)

## Overview

Local compliance policy registry loader. No NetBox writes. No SSH/SNMP/NETCONF. No automatic remediation.

The policy registry is a collection of 13 required YAML files that define compliance rules, naming conventions, dependency maps, and discovery elements.

---

## Policy Registry Loader

Module: `webui/services/compliance_policy_loader.py`

### Functions

#### `load_compliance_policy_registry(policy_dir="policies/compliance")`

Load all YAML policy files from a directory into a registry dict.

**Returns:**
```python
{
    "policy_dir": str,        # absolute path to policy dir
    "files": {                # all loaded YAML files keyed by relative path
        "bgp-policy.yaml": {...},
        "interface-policy.yaml": {...},
        ...
    },
    "policies": {},           # (reserved for future use)
    "warnings": [...],        # non-fatal issues (missing optional files)
    "blockers": [...],        # fatal issues (missing required files, YAML errors)
    "validation": {...},      # validation result dict
    "summary": {...}          # summary dict
}
```

#### `load_policy_file(path)`

Load a single YAML file and return its dict.

**Args:**
- `path` (str | Path) — path to .yaml file

**Returns:** dict (parsed YAML)

**Raises:**
- `FileNotFoundError` — file does not exist
- `ValueError` — file is not a YAML mapping
- `RuntimeError` — PyYAML not installed

#### `validate_required_policy_files(registry)`

Check mandatory and optional policy files against registry.

**Returns:**
```python
{
    "required_files": [...],         # list of 13 required file names
    "optional_files": [...],         # list of optional files
    "missing_required": [...],       # required files not found
    "missing_optional": [...],       # optional files not found
    "blockers": [...],               # fatal issues
    "warnings": [...],               # non-fatal issues
    "valid": bool                    # true iff no missing required + no blockers
}
```

#### `get_policy(registry, policy_name)`

Return one named policy by name (basename or full path).

**Args:**
- `registry` (dict) — registry from `load_compliance_policy_registry()`
- `policy_name` (str) — e.g., "bgp-policy.yaml" or "interface-policy.yaml"

**Returns:** dict (the policy file contents, or {} if not found)

#### `summarize_policy_registry(registry)`

Generate a summary of loaded policies.

**Returns:**
```python
{
    "policy_dir": str,
    "file_count": int,
    "required_count": int,
    "optional_count": int,
    "blocker_count": int,
    "warning_count": int,
    "policy_names": [...]  # sorted list of file basenames
}
```

---

## Required Policy Files

All 13 must exist. If any missing, validation returns `valid: false` and adds blockers.

| File | Purpose |
|------|---------|
| `discovery-elements.yaml` | Device/interface/VRF/BGP/prefix/community/as-path element discovery methods |
| `dependency-map.yaml` | Dependency relationships and constraints |
| `naming-conventions.yaml` | Interface, VRF, route-policy, prefix, community, as-path naming patterns |
| `snmp-policy.yaml` | SNMP version, v3 fields, OID discovery, credentials |
| `interface-policy.yaml` | Interface base and service inventory rules, naming, role mapping |
| `vrf-policy.yaml` | VRF types, validation rules, BGP/interface binding |
| `bgp-policy.yaml` | BGP peer metadata, session types, policies, community handling |
| `route-policy-policy.yaml` | Route-policy definition, nodes, validation rules, best practices |
| `ip-prefix-policy.yaml` | Prefix-list definition, entries, validation, reuse patterns |
| `community-policy.yaml` | BGP community definition, formats, examples, filter references |
| `as-path-policy.yaml` | AS path filter regex syntax, examples, validation, debugging |
| `comments-policy.yaml` | Comment field constraints, validation rules, evidence formats |
| `compliance-severity-policy.yaml` | Severity levels, rule → severity mapping, UI/workflow enforcement |

---

## Optional Policy Files

If missing, validation adds warnings but does not fail.

- `ssh-readonly-collection-policy.yaml`
- `collection-profiles/default-readonly.yaml`
- `collection-profiles/huawei-ne8000-readonly.yaml`

---

## PyYAML Requirement

`load_compliance_policy_registry()` and `load_policy_file()` require PyYAML.

**No silent fallback.** If PyYAML is absent:
```python
RuntimeError: PyYAML is required to load compliance policy registry
```

---

## Validation

Registry is considered **valid** iff:
1. All 13 required files are present
2. No YAML parse errors or file I/O errors
3. All files are valid YAML mappings

**Invalid** if any required file is missing or any blocker is recorded.

---

## Safety Guarantees

✓ **No NetBox access** — local files only  
✓ **No device connections** — no SSH, SNMP, NETCONF  
✓ **No writes** — read-only file operations  
✓ **No automatic remediation** — policy is input to compare, not action  

---

## Example Usage

```python
from webui.services.compliance_policy_loader import load_compliance_policy_registry, get_policy

registry = load_compliance_policy_registry("policies/compliance")
if not registry["validation"]["valid"]:
    print(f"Policy registry invalid: {registry['validation']['blockers']}")
    raise ValueError("Policy registry is invalid")

bgp_policy = get_policy(registry, "bgp-policy.yaml")
interface_policy = get_policy(registry, "interface-policy.yaml")
```

---

## References

- **FASE COMPLIANCE-COMPARE-001** — Policy Registry Loader
- **FASE COMPLIANCE-COMPARE-002** — Parsed Inventory vs Policy Compare
- **Service:** `webui/services/compliance_compare.py` — uses policy registry to compare devices
