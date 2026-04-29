# Compliance Policy Registry

Centralized registry of Huawei VRP/BGP_Manager configuration elements, discovery methods, naming conventions, and validation policies.

## Files

- **discovery-elements.yaml**: Element definitions, keys, and discovery commands
- **dependency-map.yaml**: Cross-element dependencies
- **naming-conventions.yaml**: Regex patterns for interface, route-policy, prefix, community, AS-path
- **snmp-policy.yaml**: SNMP version, credential handling
- **interface-policy.yaml**: Base vs service interface requirements
- **vrf-policy.yaml**: VRF naming and structure
- **bgp-policy.yaml**: BGP peer requirements, fields, criticality
- **route-policy-policy.yaml**: Route-policy node structure and filters
- **ip-prefix-policy.yaml**: IP prefix list validation
- **community-policy.yaml**: Community and community-filter rules
- **as-path-policy.yaml**: AS-path filter rules
- **comments-policy.yaml**: Comment, evidence, notes validation

## Usage

convention_validator.py loads and validates against these YAML files.

Web UI uses convention_validator to:
- Classify interfaces (base_inventory vs service_interface)
- Validate naming patterns
- Check dependencies
- Enforce structural requirements

Local tools (validate_compliance_policies.py) validate YAML integrity and generate compliance report.

## Rule IDs

Format: `CATEGORY-NNN`

- IFACE-001 to IFACE-003: Interface validation
- VRF-001: VRF naming
- RTPOL-001: Route-policy naming
- PREFIX-001: IP prefix naming
- COMM-001 to COMM-002: Community validation
- ASPATH-001: AS-path filter
- SNMP-001 to SNMP-002: SNMP policy
- BGP-001 to BGP-004: BGP metadata
- IPMAP-001 to IPMAP-002: IP address mapping
- COMMENT-001 to COMMENT-002: Comment validation
