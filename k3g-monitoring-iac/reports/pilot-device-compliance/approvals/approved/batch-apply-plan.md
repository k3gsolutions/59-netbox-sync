# Batch Staged Apply Plan — 33423d0a

**Device:** 4WNET-MNS-KTG-RX
**Total Items:** 2
**Max Items:** 3
**Readiness Status:** ready
**Generated:** 2026-04-28T17:30:34.466134+00:00

🟢 **READY** — all items pass validation

## 1. Items

### Item 1: Eth-Trunk1
- approval_id: fb0a50b3...
- object_type: interface

### Item 2: GigabitEthernet0/5/0
- approval_id: d1dce466...
- object_type: interface

## 2. Gates

✓ total_items <= max_items
✓ batch size <= 2 (pilot limit)
✓ all items are interface/base_inventory
✓ method = POST
✓ no PATCH/DELETE
✓ approval_ids unique
✓ object_keys unique

## 4. Write Policy

- real_apply_enabled: False
- write_token_provided: False
- max_items: 3

## 5. Security

- Zero secrets in payload ✓
- Token NOT in args ✓
- Token NOT in output ✓
- No PATCH/DELETE ✓
- All-or-none preflight required ✓

## 6. Next Steps

1. Review this plan
2. Execute validate_batch_staged_apply_plan.py
3. Execute dry-run: apply_batch_staged_netbox_objects.py (without --confirm-real-write-batch)
4. Review dry-run result
5. If OK, execute real write (with --confirm-real-write-batch + NETBOX_WRITE_TOKEN)
