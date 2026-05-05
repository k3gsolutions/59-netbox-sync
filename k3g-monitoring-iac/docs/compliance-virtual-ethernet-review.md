# Virtual-Ethernet Review

Local-only review for:
- `Virtual-Ethernet0/2/100.100`
- `Virtual-Ethernet0/2/101.100`
- `Virtual-Ethernet0/2/200.100`

## Read

These are Huawei logical interfaces / subinterfaces. The current naming policy may be too strict for this family.

## Suggested outcome

- Policy: add allowlist or logical-interface category for Huawei Virtual-Ethernet subinterfaces.
- Parser: keep parser local-only; no device reconnect is needed for this review.
- Severity: keep as warning unless future evidence shows a true operational risk.

## Safety

- No NetBox write
- No `/sync`
- No ApprovalRecord
- No ApplyPlan
- No automatic promotion
