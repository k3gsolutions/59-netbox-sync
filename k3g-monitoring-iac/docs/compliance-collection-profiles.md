# Compliance Collection Profiles

## Goal

Reduce collection risk by selecting safe command sets per vendor and platform.

## Profile Files

- `policies/compliance/collection-profiles/default-readonly.yaml`
- `policies/compliance/collection-profiles/huawei-ne8000-readonly.yaml`

## Selection

- Huawei + NE8000 uses `huawei-ne8000-readonly`
- Unknown vendor/model falls back to `default-readonly`

## Rules

- Profile commands must still pass the SSH read-only policy
- Profile is invalid if it contains forbidden commands or forbidden patterns
- No full configuration dump by default

## Result

Collection plan now stores:

- `collection_profile`
- `planned_commands`

