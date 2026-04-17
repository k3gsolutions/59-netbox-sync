def build_plan(inventory):
    return {
        "interfaces_detected": len(inventory.interfaces),
        "ip_addresses_detected": len(inventory.ip_addresses),
        "vlans_detected": len(inventory.vlans),
        "vrfs_detected": len(inventory.vrfs),
        "bgp_sessions_detected": len(inventory.bgp_sessions),
        "ready_for_netbox_sync": True,
    }