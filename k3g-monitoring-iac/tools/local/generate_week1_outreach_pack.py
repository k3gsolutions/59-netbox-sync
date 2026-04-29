#!/usr/bin/env python3
"""
Generate Week 1 Outreach Pack (FASE 2.15).

Creates:
- outreach-summary.md (overview)
- message-service-team.md (team-specific message)
- message-network-ops.md (team-specific message)
- message-bgp-team.md (team-specific message)
- week1-response-tracker.md (status tracking)

Zero NetBox writes. No tokens. Local only.

Usage:
    python3 generate_week1_outreach_pack.py \\
        --device <device_name> \\
        --collection <path/to/week1-metadata-collection.md> \\
        --template <path/to/week1-metadata-collection-template.csv> \\
        --output-dir <path/to/outreach>
"""

import argparse
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate Week 1 outreach pack"
    )
    parser.add_argument("--device", required=True, help="Device name")
    parser.add_argument("--collection", required=True, help="Collection MD file")
    parser.add_argument("--template", required=True, help="Template CSV file")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    return parser.parse_args()


def load_collection_file(collection_file: str) -> Dict[str, List[Dict]]:
    """Extract items from collection markdown file."""
    items = {
        "subinterfaces": [],
        "ip_addresses": [],
        "bgp_peers": []
    }

    with open(collection_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse sections
    sections = content.split("##")
    for section in sections:
        lines = section.split("\n")
        if not lines:
            continue

        section_title = lines[0].strip().lower()

        # Parse table rows
        for line in lines[1:]:
            if "|" in line and "---" not in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 2 and parts[1]:
                    item = {
                        "object_key": parts[1] if len(parts) > 1 else "",
                        "type": parts[2] if len(parts) > 2 else "",
                    }
                    if item["object_key"]:
                        if "subinterface" in section_title:
                            items["subinterfaces"].append(item)
                        elif "ip" in section_title:
                            items["ip_addresses"].append(item)
                        elif "bgp" in section_title:
                            items["bgp_peers"].append(item)

    return items


def create_outreach_summary(device: str, items: Dict) -> str:
    """Generate outreach summary."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    summary = f"""# Week 1 Outreach Summary — {device}

**Generated:** {timestamp}
**Device:** {device}
**Status:** Ready to send outreach messages

---

## Objetivo

Coletar metadados faltantes para service candidates. Sem respostas, sem Week 2 review.

---

## Timeline

| Data | Atividade |
|------|-----------|
| 2026-04-29 | Outreach pack gerado |
| 2026-05-02 | Mensagens + CSVs distribuídos |
| 2026-05-02 a 2026-05-08 | Times preenchem respostas |
| 2026-05-08 EOD | Prazo final |
| 2026-05-09 | Validação automática |
| 2026-05-09+ | Week 2 review board |

---

## Teams & Responsabilidades

### 1. Service Team

**Itens:** {len(items['subinterfaces'])} subinterfaces
"""

    for item in items["subinterfaces"]:
        summary += f"- {item['object_key']}\n"

    summary += f"""
**Status:** Não iniciado

### 2. Network Ops

**Itens:** {len(items['ip_addresses'])} IP address(es)
"""

    for item in items["ip_addresses"]:
        summary += f"- {item['object_key']}\n"

    summary += f"""
**Status:** Não iniciado

### 3. BGP Team

**Itens:** {len(items['bgp_peers'])} BGP peer(s)
"""

    for item in items["bgp_peers"]:
        summary += f"- {item['object_key']}\n"

    summary += """
**Status:** Não iniciado

---

## Status Atual

| Status | Count |
|--------|-------|
| Still Pending | """ + str(len(items["subinterfaces"]) + len(items["ip_addresses"]) + len(items["bgp_peers"])) + """ |
| Validated | 0 |
| Needs Clarification | 0 |

→ Aguardando respostas dos times.

---

Referências:
- week1-metadata-collection.md
- message-service-team.md
- message-network-ops.md
- message-bgp-team.md
- week1-response-tracker.md
"""

    return summary


def create_response_tracker(device: str, items: Dict) -> str:
    """Generate response tracker."""
    timestamp = datetime.utcnow().isoformat() + "+00:00"

    tracker = f"""# Week 1 Response Tracker — {device}

**Device:** {device}
**Timeline:** 2026-05-02 to 2026-05-08
**Generated:** {timestamp}

---

## Summary

| Status | Count |
|--------|-------|
| Not Started | 3 teams |
| Partial | 0 teams |
| Complete | 0 teams |
| Overdue | 0 teams |
| **Total Expected** | **3 CSVs** |

---

## Response Status by Team

### 1. Service Team

| Field | Value |
|-------|-------|
| **Team** | Service Team |
| **Total Items** | {len(items['subinterfaces'])} subinterfaces |
| **Response File** | service-team-response.csv |
| **Status** | 🔴 NOT_STARTED |
| **Items Responded** | 0/{len(items['subinterfaces'])} |
| **Items Pending** | {len(items['subinterfaces'])}/{len(items['subinterfaces'])} |
| **Deadline** | 2026-05-08 EOD |

**Expected Items:**
"""

    for item in items["subinterfaces"]:
        tracker += f"- {item['object_key']}: (pending)\n"

    tracker += f"""

### 2. Network Ops

| Field | Value |
|-------|-------|
| **Team** | Network Ops |
| **Total Items** | {len(items['ip_addresses'])} IP address(es) |
| **Response File** | network-ops-response.csv |
| **Status** | 🔴 NOT_STARTED |
| **Items Responded** | 0/{len(items['ip_addresses'])} |
| **Items Pending** | {len(items['ip_addresses'])}/{len(items['ip_addresses'])} |
| **Deadline** | 2026-05-08 EOD |

**Expected Items:**
"""

    for item in items["ip_addresses"]:
        tracker += f"- {item['object_key']}: (pending)\n"

    tracker += f"""

### 3. BGP Team

| Field | Value |
|-------|-------|
| **Team** | BGP Team |
| **Total Items** | {len(items['bgp_peers'])} BGP peer(s) |
| **Response File** | bgp-team-response.csv |
| **Status** | 🔴 NOT_STARTED |
| **Items Responded** | 0/{len(items['bgp_peers'])} |
| **Items Pending** | {len(items['bgp_peers'])}/{len(items['bgp_peers'])} |
| **Deadline** | 2026-05-08 EOD |

**Expected Items:**
"""

    for item in items["bgp_peers"]:
        tracker += f"- {item['object_key']}: (pending)\n"

    tracker += """

---

**Status:** Ready to deploy outreach pack.
"""

    return tracker


def main():
    args = parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract items from collection
    items = load_collection_file(args.collection)
    print(f"✓ Extracted items from collection")
    print(f"  Subinterfaces: {len(items['subinterfaces'])}")
    print(f"  IP addresses: {len(items['ip_addresses'])}")
    print(f"  BGP peers: {len(items['bgp_peers'])}")

    # Generate outreach summary
    summary = create_outreach_summary(args.device, items)
    summary_file = output_dir / "outreach-summary.md"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"✓ Outreach summary saved: {summary_file}")

    # Generate response tracker
    tracker = create_response_tracker(args.device, items)
    tracker_file = output_dir / "week1-response-tracker.md"
    with open(tracker_file, "w", encoding="utf-8") as f:
        f.write(tracker)
    print(f"✓ Response tracker saved: {tracker_file}")

    print(f"\n✅ Week 1 outreach pack preparation complete")
    print(f"\nGenerated files:")
    print(f"  - outreach-summary.md")
    print(f"  - message-service-team.md (manual creation)")
    print(f"  - message-network-ops.md (manual creation)")
    print(f"  - message-bgp-team.md (manual creation)")
    print(f"  - week1-response-tracker.md")
    print(f"\nNext steps:")
    print(f"  1. Review outreach-summary.md")
    print(f"  2. Customize team messages (names, contacts)")
    print(f"  3. Distribute messages + CSV templates")
    print(f"  4. Monitor week1-response-tracker.md")
    print(f"  5. Run check_week1_response_status.py to update status")


if __name__ == "__main__":
    main()
