#!/usr/bin/env python3
"""Validate compliance policy YAML files."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def validate_yaml_files(policies_dir: Path) -> Dict[str, Any]:
    """Validate all YAML files in policies/compliance/."""
    results = {
        "summary": {"total": 0, "valid": 0, "invalid": 0},
        "files": {},
        "errors": [],
    }

    if not HAS_YAML:
        results["errors"].append("PyYAML not installed; skipping validation")
        return results

    yaml_files = [
        "discovery-elements.yaml",
        "dependency-map.yaml",
        "naming-conventions.yaml",
        "snmp-policy.yaml",
        "interface-policy.yaml",
        "vrf-policy.yaml",
        "bgp-policy.yaml",
        "route-policy-policy.yaml",
        "ip-prefix-policy.yaml",
        "community-policy.yaml",
        "as-path-policy.yaml",
        "comments-policy.yaml",
    ]

    for filename in yaml_files:
        filepath = policies_dir / filename
        results["summary"]["total"] += 1
        file_result = {"status": "valid", "errors": []}

        if not filepath.exists():
            file_result["status"] = "missing"
            file_result["errors"].append(f"File not found: {filepath}")
            results["summary"]["invalid"] += 1
            results["files"][filename] = file_result
            continue

        try:
            with filepath.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if data is None:
                file_result["status"] = "invalid"
                file_result["errors"].append("File is empty or invalid YAML")
                results["summary"]["invalid"] += 1
            else:
                # Validate structure based on filename
                if "naming-conventions" in filename:
                    _validate_naming_conventions(data, file_result)
                elif "discovery-elements" in filename:
                    _validate_discovery_elements(data, file_result)
                elif "dependency-map" in filename:
                    _validate_dependency_map(data, file_result)
                elif "policy" in filename:
                    _validate_policy_file(data, filename, file_result)

                if file_result["errors"]:
                    file_result["status"] = "invalid"
                    results["summary"]["invalid"] += 1
                else:
                    results["summary"]["valid"] += 1

        except yaml.YAMLError as exc:
            file_result["status"] = "invalid"
            file_result["errors"].append(f"YAML syntax error: {exc}")
            results["summary"]["invalid"] += 1
        except Exception as exc:
            file_result["status"] = "invalid"
            file_result["errors"].append(f"Error: {exc}")
            results["summary"]["invalid"] += 1

        results["files"][filename] = file_result

    return results


def _validate_naming_conventions(data: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Validate naming-conventions.yaml structure."""
    if not isinstance(data, dict):
        result["errors"].append("Root must be dict")
        return

    for category, config in data.items():
        if not isinstance(config, dict):
            result["errors"].append(f"{category} must be dict")
            continue

        if "patterns" in config:
            patterns = config["patterns"]
            if not isinstance(patterns, list):
                result["errors"].append(f"{category}.patterns must be list")
            else:
                for i, pattern in enumerate(patterns):
                    try:
                        re.compile(pattern)
                    except re.error as exc:
                        result["errors"].append(f"{category}.patterns[{i}]: invalid regex: {exc}")

        if "pattern" in config:
            pattern = config["pattern"]
            try:
                re.compile(pattern)
            except re.error as exc:
                result["errors"].append(f"{category}.pattern: invalid regex: {exc}")


def _validate_discovery_elements(data: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Validate discovery-elements.yaml structure."""
    if not isinstance(data, dict):
        result["errors"].append("Root must be dict")
        return

    for element, config in data.items():
        if not isinstance(config, dict):
            result["errors"].append(f"{element} must be dict")
            continue

        if "keys" in config and not isinstance(config["keys"], list):
            result["errors"].append(f"{element}.keys must be list")

        if "discovery" in config and not isinstance(config["discovery"], list):
            result["errors"].append(f"{element}.discovery must be list")


def _validate_dependency_map(data: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Validate dependency-map.yaml structure."""
    if not isinstance(data, dict):
        result["errors"].append("Root must be dict")
        return

    for element, deps in data.items():
        if not isinstance(deps, dict):
            continue
        if "required" in deps and not isinstance(deps["required"], list):
            result["errors"].append(f"{element}.required must be list")
        if "optional" in deps and not isinstance(deps["optional"], list):
            result["errors"].append(f"{element}.optional must be list")


def _validate_policy_file(data: Dict[str, Any], filename: str, result: Dict[str, Any]) -> None:
    """Validate policy file structure."""
    if not isinstance(data, dict):
        result["errors"].append("Root must be dict")
        return

    # Basic structure check for policy files
    for key, value in data.items():
        if not isinstance(value, (dict, list, str, int, bool, type(None))):
            result["errors"].append(f"Invalid type for {key}: {type(value)}")


def generate_report(results: Dict[str, Any], output_file: Path) -> None:
    """Generate markdown report from validation results."""
    lines = [
        "# Compliance Policy Validation Report",
        "",
        f"**Generated:** {Path(__file__).name}",
        "",
        "## Summary",
        "",
        f"- **Total Files:** {results['summary']['total']}",
        f"- **Valid:** {results['summary']['valid']}",
        f"- **Invalid:** {results['summary']['invalid']}",
        "",
    ]

    if results["errors"]:
        lines.extend([
            "## General Errors",
            "",
        ])
        for error in results["errors"]:
            lines.append(f"- {error}")
        lines.append("")

    lines.extend([
        "## File Validation Results",
        "",
    ])

    for filename, file_result in results["files"].items():
        status_icon = "✅" if file_result["status"] == "valid" else "❌"
        lines.append(f"### {status_icon} {filename}")
        lines.append(f"**Status:** {file_result['status']}")
        if file_result["errors"]:
            lines.append("")
            lines.append("**Errors:**")
            for error in file_result["errors"]:
                lines.append(f"- {error}")
        lines.append("")

    output_file.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    """Run validation."""
    root = Path(__file__).parent.parent.parent
    policies_dir = root / "policies" / "compliance"
    output_file = root / "reports" / "compliance-policy-validation.md"

    print(f"Validating policies in {policies_dir}")

    if not policies_dir.exists():
        print(f"ERROR: {policies_dir} does not exist")
        return 1

    results = validate_yaml_files(policies_dir)

    # Generate report
    output_file.parent.mkdir(parents=True, exist_ok=True)
    generate_report(results, output_file)
    print(f"Report generated: {output_file}")

    # Print summary
    print("")
    print("=" * 60)
    print(f"Results: {results['summary']['valid']}/{results['summary']['total']} files valid")
    print("=" * 60)

    return 0 if results["summary"]["invalid"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
