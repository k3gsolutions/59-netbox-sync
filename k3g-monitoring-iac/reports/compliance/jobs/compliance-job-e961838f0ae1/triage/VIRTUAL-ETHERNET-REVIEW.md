# VIRTUAL-ETHERNET-REVIEW

## Job ID
`compliance-job-e961838f0ae1`

## Findings

### Virtual-Ethernet0/2/100.100
- finding_id: CMP-ECD73947B0
- rule_id: interface.naming.invalid
- triage_bucket: likely_policy_too_strict
- confidence: high
- reason: Interface Huawei válida parece bater em policy interna rígida demais.
- policy_suggestion: Adicionar allowlist para Virtual-Ethernet e subinterfaces Huawei legítimas.
- parser_suggestion: Manter parser; a separação de brief parece correta. Tratar logical_interface como categoria própria.
- severity_suggestion: warning

### Virtual-Ethernet0/2/101.100
- finding_id: CMP-48B6DA3065
- rule_id: interface.naming.invalid
- triage_bucket: likely_policy_too_strict
- confidence: high
- reason: Interface Huawei válida parece bater em policy interna rígida demais.
- policy_suggestion: Adicionar allowlist para Virtual-Ethernet e subinterfaces Huawei legítimas.
- parser_suggestion: Manter parser; a separação de brief parece correta. Tratar logical_interface como categoria própria.
- severity_suggestion: warning

### Virtual-Ethernet0/2/200.100
- finding_id: CMP-8412059E0F
- rule_id: interface.naming.invalid
- triage_bucket: likely_policy_too_strict
- confidence: high
- reason: Interface Huawei válida parece bater em policy interna rígida demais.
- policy_suggestion: Adicionar allowlist para Virtual-Ethernet e subinterfaces Huawei legítimas.
- parser_suggestion: Manter parser; a separação de brief parece correta. Tratar logical_interface como categoria própria.
- severity_suggestion: warning

## Overall Suggestions
- policy: Adicionar allowlist para Virtual-Ethernet e subinterfaces Huawei legítimas.
- parser: Manter parser; a separação de brief parece correta. Tratar logical_interface como categoria própria.
- severity: warning
