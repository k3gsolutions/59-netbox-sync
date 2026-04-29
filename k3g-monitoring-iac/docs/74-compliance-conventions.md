# Compliance Conventions & Policy Registry

## Overview

Centralized registry of Huawei VRP/BGP_Manager configuration policies, discovery methods, naming conventions, and dependencies. Forms the basis for validation in Web UI and local tools.

**Location:** `policies/compliance/` (YAML registry files)
**Validator:** `webui/services/convention_validator.py`

---

## VRP Element Tree

### Device
- **Keys:** hostname, sys_name, sys_descr, uptime, vendor, platform, model
- **Discovery:**
  - SNMP sysDescr (OID 1.3.6.1.2.1.1.1.0)
  - SNMP sysUpTime (OID 1.3.6.1.2.1.1.3.0)
  - SNMP sysName (OID 1.3.6.1.2.1.1.5.0)
  - CLI `display version`

### Interface
- **Keys:** name, type, admin_status, oper_status, protocol_status, description, ip_addresses, vrf, parent_interface, vlan_id
- **Discovery:**
  - CLI `display interface brief`
  - CLI `display interface`
  - CLI `display current-configuration interface`

### VRF / VPN Instance
- **Keys:** name, rd, route_targets_import, route_targets_export, description, tenant
- **Discovery:**
  - CLI `display current-configuration | include ip vpn-instance`

### BGP Global
- **Keys:** local_asn, router_id, address_families
- **Discovery:**
  - CLI `display bgp peer`
  - CLI `display bgp ipv6 peer`
  - CLI `display current-configuration | include bgp`

### BGP Peer
- **Keys:** peer_ip, afi, safi, remote_asn, local_asn, state, description, connect_interface, vrf, peer_group, import_policy, export_policy, received_prefixes, advertised_prefixes, uptime, last_error, service_type, criticality, owner
- **Discovery:**
  - CLI `display bgp peer`
  - CLI `display bgp ipv6 peer`
  - CLI `display bgp peer <peer> verbose`
  - CLI `display bgp vpnv4 vpn-instance <vrf> peer`
  - CLI `display bgp vpnv6 vpn-instance <vrf> peer`

### BGP Prefix Observation
- **Keys:** peer_ip, vrf, afi, direction, prefix, as_path, next_hop, local_pref, med, community, valid, best
- **Discovery:**
  - CLI `display bgp routing-table peer <peer> received-routes`
  - CLI `display bgp routing-table peer <peer> advertised-routes`

### Route-Policy
- **Keys:** name, nodes, referenced_by_peers
- **Discovery:**
  - CLI `display current-configuration | include route-policy`

### Route-Policy Node
- **Keys:** policy_name, node_id, action, if_match_ip_prefix, if_match_community_filter, if_match_as_path_filter, apply_community, apply_community_list, apply_local_preference, apply_med, comments

### IP Prefix List
- **Keys:** name, afi, index, action, prefix, greater_equal, less_equal, referenced_by_route_policy
- **Discovery:**
  - CLI `display current-configuration | include 'ip ip-prefix'`

### Community Filter
- **Keys:** filter_id, name, type, action, community, regex, referenced_by_route_policy
- **Discovery:**
  - CLI `display current-configuration | include 'community-filter'`

### AS-Path Filter
- **Keys:** filter_id, name, action, regex, referenced_by_route_policy
- **Discovery:**
  - CLI `display current-configuration | include 'ip as-path-filter'`

---

## Dependencies

### BGP Peer requires:
- device ✓
- bgp_global ✓
- peer_ip ✓
- remote_asn ✓
- [Optional: connect_interface, vrf, import_policy, export_policy, peer_group]

### BGP VPN Peer requires:
- device ✓
- bgp_global ✓
- vrf ✓
- peer_ip ✓
- remote_asn ✓

### Route-Policy Node requires:
- route_policy ✓
- node_id ✓
- action ✓
- [Optional: if_match_ip_prefix, if_match_community_filter, if_match_as_path_filter]

### Route-Policy can reference:
- ip_prefix_list
- community_filter
- as_path_filter
- **Constraint:** All referenced filters must be defined

### IP Address Mapping requires:
- address ✓
- relation_type ✓
- [Optional: interface, vrf]
- **Conditional:**
  - If relation_type = "service" → service_relation required
  - If relation_type = "unknown" → notes required

---

## Naming Conventions

### Interface

**Base Inventory Patterns:**
- `Eth-Trunk\d+` → Eth-Trunk0, Eth-Trunk1
- `GigabitEthernet\d+/\d+/\d+` → GigabitEthernet0/0/1
- `10GE\d+/\d+/\d+` → 10GE0/1/0
- `LoopBack\d+` → LoopBack0
- `NULL\d+` → NULL0
- `Vlanif\d+` → Vlanif100

**Service Interface Patterns:**
- `Eth-Trunk\d+\.\d+` → Eth-Trunk0.147, Eth-Trunk0.1580
- `GigabitEthernet\d+/\d+/\d+\.\d+` → GigabitEthernet0/5/0.100
- `10GE\d+/\d+/\d+\.\d+` → 10GE0/1/0.100

**Service Interface Requirements:**
- description (min 10 chars, max 200)
- tenant
- service_type (customer-internet, customer-l2vpn, customer-l3vpn, customer-transport, carrier-transit, carrier-peering, ix-public, cdn-cache, infra-backbone, infra-management)
- criticality (platinum, gold, silver, bronze)
- owner

### VRF

**Pattern:** `[a-zA-Z0-9_\-]+`
**Max Length:** 100 chars
**Reserved:** `default`, `_public_`

**Examples:**
- customer-a
- mpls-backbone
- management
- infra_monitoring

### Route-Policy

**Convention:** `AS<ASN>-<SITE>-<CONTEXT>-<SERVICE>-IPv[46]-<Import|Export>`

**Pattern:** `^AS\d+-[A-Z0-9]+-[A-Z0-9]+-\w+-IPv[46]-(Import|Export)$`

**Parts:**
- ASN: Local ASN (e.g., 263934)
- SITE: Site code (e.g., INFORR, BVA)
- CONTEXT: Service or context (e.g., BVA, InterCDN)
- SERVICE: Service name
- AFI: IPv4 or IPv6
- DIRECTION: Import or Export

**Examples:**
- AS263934-INFORR-BVA-InterCDN-IPv4-Export
- AS263934-INFORR-BACKBONE-IPv4-Import
- AS64512-TRANSIT-UPLINK-IPv4-Import

### IP Prefix List

**Pattern:** `(BOGONS|CUSTOMER|CDN|IX|TRANSIT|INFRA)-<NAME>-IPv[46]`

**Examples:**
- BOGONS-IPv4, BOGONS-IPv6
- CUSTOMER-CLIENTEABC-IPv4
- CDN-AKAMAI-IPv6
- IX-NANOG-IPv4
- TRANSIT-ISP-IPv4
- INFRA-BACKBONE-IPv4

### Community

**Format:** `ASN:VALUE`
**Pattern:** `^\d+:\d+$`
**ASN Range:** 1-4294967295
**VALUE Range:** 0-65535

**Examples:**
- 263934:100 (peer identifier)
- 263934:200 (service type)
- 263934:1000 (criticality platinum)

### AS-Path Filter

**Format:** Regular expression for AS-path matching
**Special Chars:** `.`, `*`, `+`, `?`, `|`, `[]`, `()`, `^`, `_`

**Examples:**
- `^65000$` (direct peer)
- `^65000(_\d+)?$` (direct or via one intermediate)
- `^(?!.*65000).*$` (avoid ASN 65000)

---

## Policies

### SNMP Policy

**Preferred Version:** SNMPv3
**Allowed Versions:** v3 (required), v2c (legacy only)

**v2c Blocked Communities:**
- public
- private
- secret
- admin
- cisco
- snmp

**v3 Required Fields:**
- username
- auth_protocol (MD5, SHA, SHA-256, SHA-384, SHA-512)
- auth_password
- privacy_protocol (DES, AES, AES-192, AES-256)
- privacy_password

**Credential Sources:**
- NetBox secret (device scope)
- NetBox custom field (device scope)
- NetBox custom field (tenant scope)
- Local encrypted file (not committed to git)

### BGP Policy

**Required for All Peers:**
- peer_ip
- remote_asn
- description
- owner

**Required for Service Peers:**
- criticality

**Required for External BGP:**
- import_policy
- export_policy

**Optional but Recommended:**
- peer_group
- connect_interface
- vrf

### Route-Policy Policy

**Node Requirements:**
- node_id (sequence number)
- action (permit or deny)

**Node Constraints:**
- All referenced prefix-lists must exist
- All referenced community-filters must exist
- All referenced AS-path filters must exist

### Interface Policy

**Base Inventory:**
- Optional: description, mtu, enabled, type

**Service Interface:**
- Required: description, tenant, service_type, criticality, owner
- Optional: vrf, vlan_id, parent_interface, protocol_status

### Comment Policy

**Blocked Keywords:** token, password, secret, private key, bearer, api_key, ssh_key

**Max Lengths:**
- Short comments: 255 chars
- Evidence/notes: 1024 chars

**Required When:**
- evidence: answered status for any response
- notes: blocked/rejected/needs_clarification status

---

## Rule IDs & Severity

| Rule ID | Description | Severity |
|---------|-------------|----------|
| IFACE-001 | Base interface pattern invalid | error |
| IFACE-002 | Service subinterface pattern invalid | error |
| IFACE-003 | Service interface missing required fields | error |
| VRF-001 | VRF name pattern invalid | error |
| RTPOL-001 | Route-policy naming convention violation | error |
| PREFIX-001 | IP prefix naming convention violation | error |
| COMM-001 | Community not in ASN:VALUE format | error |
| COMM-002 | Community filter reference not found | error |
| ASPATH-001 | AS-path filter regex invalid | error |
| SNMP-001 | SNMP community blocked | blocker |
| SNMP-002 | SNMP version below v3 | warning |
| BGP-001 | BGP peer missing remote_asn | error |
| BGP-002 | BGP peer missing owner | error |
| BGP-003 | BGP peer missing policy_intent | error |
| BGP-004 | BGP peer criticality missing for service | error |
| IPMAP-001 | relation_type=service without service_relation | error |
| IPMAP-002 | relation_type=unknown without notes | error |
| COMMENT-001 | Comment contains blocked keyword | blocker |
| COMMENT-002 | Comment exceeds max length | error |

---

## Usage in Web UI

**convention_validator.py** functions are called:

1. **Before saving responses:**
   - Validate interface names
   - Validate VRF names
   - Validate BGP metadata
   - Validate comments/evidence/notes

2. **Validation errors:**
   - Severity = blocker → Block save
   - Severity = error → Show warning, allow save with confirmation
   - Severity = warning → Show advisory, allow save
   - Severity = info → Informational only

3. **During form rendering:**
   - classify_interface() to determine required fields
   - parse_route_policy_name() to extract components for documentation

---

## Files

| File | Purpose |
|------|---------|
| discovery-elements.yaml | VRP elements, keys, discovery commands |
| dependency-map.yaml | Cross-element dependencies |
| naming-conventions.yaml | Regex patterns for interface, VRF, route-policy, prefix, community |
| snmp-policy.yaml | SNMP version, community, credential handling |
| interface-policy.yaml | Base vs service interface requirements |
| vrf-policy.yaml | VRF naming, rd, rt, description |
| bgp-policy.yaml | BGP peer requirements, criticality |
| route-policy-policy.yaml | Route-policy node structure |
| ip-prefix-policy.yaml | IP prefix list validation |
| community-policy.yaml | BGP community format |
| as-path-policy.yaml | AS-path filter regex validation |
| comments-policy.yaml | Comment, evidence, notes constraints |

---

## References

- `webui/services/convention_validator.py` — Main validator
- `tools/local/test_compliance_policy_registry.py` — Test suite
- `tools/local/validate_compliance_policies.py` — YAML validation
- `reports/compliance-policy-validation.md` — Validation report
