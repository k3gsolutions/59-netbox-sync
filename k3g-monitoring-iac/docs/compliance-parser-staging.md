# Compliance Parser Staging

## Goal

Prepare collected files for parsing without exposing raw output in the UI.

## Files

- `webui/services/compliance_parser_staging.py`

## Manifest

Generated files:

- `collection-results/parser-manifest.json`
- `collection-results/PARSER-STAGING.md`

Each device entry includes:

- `raw_files`
- `redacted_files`
- `parsed_files`
- `parsed_dir`
- `ready_for_parsing`

## Safety

- raw output remains hidden from the UI
- redacted output is the default review surface
- parsed directory is staged locally only

## Next Stage

Parser staging feeds the Huawei NE8000 baseline parser and the parsed inventory artifacts written under `collection-results/devices/<device_id>/parsed/`.
