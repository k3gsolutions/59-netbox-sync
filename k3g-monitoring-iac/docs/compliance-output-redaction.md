# Compliance Output Redaction

## Goal

Mask sensitive strings before anything reaches later analysis stages or the UI.

## Files

- `webui/services/compliance_output_redaction.py`

## Redaction Rules

- `password` -> `password ****`
- `cipher` -> `cipher ****`
- `community` -> `community ****`
- `snmp-agent community` -> `snmp-agent community ****`
- tokens and secrets are masked
- config-mode indicators are flagged by validation

## Outputs

For each command:

- raw text stays in `raw/`
- redacted text goes to `redacted/`
- metadata records redaction status and sensitive finding count

## UI

- raw content is never shown
- UI uses redacted or parsed artifacts only

