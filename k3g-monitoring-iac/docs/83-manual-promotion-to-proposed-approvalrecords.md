# FASE 2.38 — Manual Promotion of Week 2 Decisions to Proposed ApprovalRecords

## Overview

**FASE 2.38** implements controlled, explicit promotion of Week 2 human review decisions to official ApprovalRecords. This phase:

- ✅ Reads human decisions from `week2-review-decisions.csv`
- ✅ Validates all promotion criteria (decision, reviewer, timestamp)
- ✅ Creates ApprovalRecords with `status=proposed` (not auto-approved)
- ✅ Generates audit trail and promotion report
- ✅ Maintains zero NetBox writes, no tokens, no ApplyPlan creation

**No automatic promotions.** Every ApprovalRecord requires explicit human decision with validated metadata.

---

## Key Components

### Input: Week 2 Review Decisions CSV

File: `reports/pilot-device-compliance/week2-review/week2-review-decisions.csv`

Required columns:
- `object_key` — Interface/route-policy/etc name
- `decision` — Must be exactly `approve_for_approval_record` to promote
- `approval_record_allowed` — Must be `true` or `1`
- `reviewer` — Name/email of approver
- `reviewed_at` — ISO 8601 datetime with timezone (e.g., `2026-04-29T10:00:00Z`)
- `reason` or `notes` — Justification (at least one required)

Example row (promotes):
```
Eth-Trunk0,approve_for_approval_record,true,John Doe,2026-04-29T10:00:00Z,Valid naming,
```

Example row (does NOT promote):
```
Eth-Trunk1,reject,false,Jane Smith,2026-04-29T10:05:00Z,Naming violation,
```

### Promotion Tool

**Script:** `tools/local/promote_week2_drafts_to_approvals.py`

**Usage:**
```bash
python3 tools/local/promote_week2_drafts_to_approvals.py \
  --device <device_name> \
  --device-id <int> \
  --decisions path/to/week2-review-decisions.csv \
  --drafts-dir path/to/week2-approval-drafts \
  --output-dir path/to/week2-review
```

**Required Arguments:**
- `--device` — Device name (e.g., `4WNET-MNS-KTG-RX`)
- `--device-id` — NetBox device ID (integer)
- `--decisions` — Path to decisions CSV
- `--drafts-dir` — Path to approval drafts (created by Week 2 review phase)
- `--output-dir` — Output directory for promoted records and report

**Optional:**
- `--report` — Custom report path (default: `{output_dir}/week2-promotion-report.md`)

---

## Promotion Criteria (ALL must be satisfied)

Tool checks each row in decisions CSV against:

1. **decision field**
   - Must equal `approve_for_approval_record` (case-insensitive)
   - Any other value → NOT promoted

2. **approval_record_allowed field**
   - Must be `true`, `1`, or `yes` (case-insensitive)
   - Any other value → NOT promoted

3. **reviewer field**
   - Must not be empty
   - Name or email required
   - Empty string → NOT promoted

4. **reviewed_at field**
   - Must be valid ISO 8601 datetime
   - Can include timezone (e.g., `+00:00` or `Z`)
   - Parses via `datetime.fromisoformat()`
   - Invalid format → NOT promoted

5. **reason or notes field**
   - At least one must be non-empty
   - Provides justification for decision
   - Both empty → NOT promoted

6. **Draft file exists and valid**
   - File: `approval-draft-{object_key_sanitized}.json`
   - Must be valid JSON
   - Must have required fields: draft_id, status=draft_review, device, device_id, object_key
   - Missing/invalid file → NOT promoted

---

## Created ApprovalRecord Structure

**Status:** `proposed` (not `approved`)

**Key fields:**
```json
{
  "approval_id": "uuid",
  "approval_record_id": "uuid",
  "status": "proposed",
  "device": "device_name",
  "device_id": 123,
  "object_type": "Interface",
  "object_key": "Eth-Trunk0",
  "action": "POST",
  "category": "base_inventory",
  "reviewer": "John Doe",
  "reviewed_at": "2026-04-29T10:00:00+00:00",
  "source_draft": "draft-001",
  "evidence_hash": "sha256:...",
  "safety": {
    "no_netbox_write": true,
    "no_apply_plan_created": true,
    "manual_review_required": true
  },
  "state_history": [
    {"from": "draft_review", "to": "draft_review_created", ...},
    {"from": "draft_review", "to": "human_review_approved_for_approval_record", ...},
    {"from": "draft_review", "to": "promoted_to_proposed", ...}
  ],
  "review": {
    "status": "proposed",
    "reviewed_by": "John Doe",
    "reviewed_at": "2026-04-29T10:00:00+00:00",
    "decision": "approve_for_approval_record"
  }
}
```

---

## Output

### Promoted ApprovalRecords

Directory: `{output_dir}/promoted/`

Files: `approval-record-{uuid}.json`

Each record contains:
- ✅ UUID approval_record_id
- ✅ status = proposed
- ✅ Full audit trail (state_history)
- ✅ Safety flags (no_netbox_write, no_apply_plan_created, manual_review_required)
- ✅ Evidence hash for integrity
- ✅ Source draft reference
- ✅ Reviewer name and timestamp

### Promotion Report

File: `{output_dir}/week2-promotion-report.md`

Sections:
1. **Summary** — Count of promoted, not promoted, missing drafts
2. **Promoted ApprovalRecords** — Table with object_key, approval_record_id, status
3. **Not Promoted** — Reasons why each decision was rejected
4. **Missing Draft Files** — Expected files not found
5. **Promotion Criteria** — Reference of all requirements
6. **Safety Confirmations** — Zero NetBox writes, no ApplyPlan, manual review required

---

## Workflow

### Before Promotion

1. Week 2 human review completed in Web UI
2. Decisions written to `week2-review-decisions.csv`
3. Drafts in `week2-approval-drafts/` directory
4. All validation done (convention, policy compliance)

### Promotion Step

```bash
python3 tools/local/promote_week2_drafts_to_approvals.py \
  --device "4WNET-MNS-KTG-RX" \
  --device-id 1890 \
  --decisions reports/pilot-device-compliance/week2-review/week2-review-decisions.csv \
  --drafts-dir reports/pilot-device-compliance/week2-review/week2-approval-drafts \
  --output-dir reports/pilot-device-compliance/week2-review
```

### After Promotion

1. ApprovalRecords created with `status=proposed`
2. Report generated showing:
   - How many promoted
   - Why others rejected
   - Full audit trail
3. Proposed ApprovalRecords ready for:
   - FASE 2.39: ApplyPlan readiness gate validation
   - Next: Manual approval/rejection workflow

---

## Security Notes

### ✅ What's Guaranteed

- No NetBox API calls (verified by `no_netbox_write` flag)
- No write tokens used
- No ApplyPlan created
- No automatic approvals (manual_review_required)
- Full audit trail with reviewer name + timestamp
- Evidence hash prevents tampering with source draft

### ⚠️ Before Running

1. Verify Week 2 review CSV is complete
2. Ensure all drafts exist in expected directory
3. Check reviewer names are valid (will appear in audit trail)
4. Confirm timestamps are ISO 8601 format

### 🔒 After Running

1. Promoted ApprovalRecords are read-only (status=proposed)
2. Do not edit JSON files directly
3. All state transitions must go through proper workflow
4. Audit trail is immutable (records when/by-whom decision made)

---

## Troubleshooting

### "Invalid state: {status}" or "Missing safety flags"
- Draft file missing required fields
- Check draft JSON structure matches `draft_review` schema
- Ensure field names match exactly (case-sensitive)

### "Draft file invalid or corrupted: approval-draft-X.json"
- File not found or invalid JSON
- Check file is in `--drafts-dir`
- Verify JSON formatting: `python3 -m json.tool approval-draft-X.json`

### "decision={X}, expected 'approve_for_approval_record'"
- Row decision value must be EXACTLY this string
- Check for typos, spaces, case sensitivity
- Only rows with this exact value are promoted

### "reviewed_at='2026-04-29 10:00:00', not valid ISO datetime"
- Must use ISO 8601 format
- Good: `2026-04-29T10:00:00Z` or `2026-04-29T10:00:00+00:00`
- Bad: `2026-04-29 10:00:00` or `04/29/2026 10am`

---

## Example: Full Promotion Run

```bash
# Setup
export DEVICE="4WNET-MNS-KTG-RX"
export DEVICE_ID="1890"
export REPORTS_DIR="reports/pilot-device-compliance"
export REVIEW_DIR="$REPORTS_DIR/week2-review"

# Run promotion
python3 tools/local/promote_week2_drafts_to_approvals.py \
  --device "$DEVICE" \
  --device-id "$DEVICE_ID" \
  --decisions "$REVIEW_DIR/week2-review-decisions.csv" \
  --drafts-dir "$REVIEW_DIR/week2-approval-drafts" \
  --output-dir "$REVIEW_DIR"

# Check output
ls -la "$REVIEW_DIR/promoted/"
cat "$REVIEW_DIR/week2-promotion-report.md"

# Verify each record
for f in "$REVIEW_DIR/promoted/approval-record-"*.json; do
  echo "=== $(basename $f) ==="
  python3 -c "import json; r=json.load(open('$f')); print(f'  Status: {r[\"status\"]}'); print(f'  Reviewer: {r[\"reviewer\"]}'); print(f'  Object: {r[\"object_key\"]}')"
done
```

---

## Next: FASE 2.39 ApplyPlan Readiness Gate

After promotion, proposed ApprovalRecords advance to **FASE 2.39** for readiness validation before ApplyPlan creation. See `docs/84-applyplan-readiness-gate.md`.

No automatic progression. Each stage requires validation.
