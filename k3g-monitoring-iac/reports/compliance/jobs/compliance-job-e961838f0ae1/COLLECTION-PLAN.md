# COLLECTION-PLAN

## Job ID
`compliance-job-e961838f0ae1`

## Decision
`COLLECTION_PLAN_PREPARED`

## Devices

### 4WNET-MNS-KTG-RX
- device_id: 1890
- primary_ip4: 104.234.244.255/32
- platform: none
- manufacturer: Huawei
- model: NE8000 M8 DC
- allowed_collection_methods:
  - ssh_read_only
  - snmp_read_only
- forbidden_methods:
  - netconf_write
  - cli_config
  - netbox_write
  - sync
- command_policy:
  - show/display only
  - no configure/system-view
  - no commit/save
- expected_outputs:
  - interfaces
  - bgp
  - vrf
  - route-policy
  - prefix-list
  - snmp
  - system info

## Safety

- No SSH execution
- No SNMP execution
- No NETCONF execution
- No NetBox write
- No /sync
