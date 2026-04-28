#!/usr/bin/env python3
"""Compare two compliance reports and generate comparison markdown."""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class ComplianceReport:
    """Parse and extract data from compliance report Markdown."""

    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        with open(self.filepath, "r", encoding="utf-8") as f:
            self.content = f.read()

        self.hostname = self._extract_field("Hostname: (.+)")
        self.device_id = self._extract_field("Device ID: (.+)")
        self.status = self._extract_field("Status geral: (.+)")
        self.total_divergences = self._extract_int("Total de divergências: (\\d+)")
        self.highest_severity = self._extract_field("Severidade mais alta: (.+)")

        self.aggregated_divergences = self._extract_divergences(
            "## 5. Divergências agregadas"
        )
        self.object_divergences = self._extract_divergences("## 6. Divergências por objeto")

    def _extract_field(self, pattern: str) -> str:
        """Extract field value from report."""
        match = re.search(pattern, self.content)
        if match:
            return match.group(1).strip()
        return None

    def _extract_int(self, pattern: str) -> int:
        """Extract integer field."""
        match = re.search(pattern, self.content)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return 0
        return 0

    def _extract_divergences(self, section_header: str) -> List[Dict]:
        """Extract divergences from a section."""
        divergences = []

        # Find section start
        section_match = re.search(rf"{re.escape(section_header)}[^\n]*\n", self.content)
        if not section_match:
            return divergences

        section_start = section_match.end()

        # Find next section (starting with ##)
        next_section = re.search(r"\n## ", self.content[section_start:])
        if next_section:
            section_end = section_start + next_section.start()
        else:
            section_end = len(self.content)

        section_content = self.content[section_start:section_end]

        # Extract table rows (lines starting with |)
        rows = re.findall(r"\n\|(.+)\|", section_content)
        if not rows:
            return divergences

        # Skip header row (contains ---)
        for row in rows[1:]:
            cells = [cell.strip() for cell in row.split("|")]

            # Try to parse divergence based on section type
            if "Divergências agregadas" in section_header:
                # Columns: Severidade | Código | Escopo | Ação preferida | Mensagem
                if len(cells) >= 5:
                    divergences.append({
                        "severity": cells[0],
                        "code": cells[1],
                        "scope": cells[2],
                        "object_type": None,
                        "object_key": None,
                        "preferred_action": cells[3],
                        "message": cells[4],
                    })
            else:
                # Columns: Severidade | Código | Tipo de objeto | Chave do objeto | Ação preferida | Mensagem
                if len(cells) >= 6:
                    divergences.append({
                        "severity": cells[0],
                        "code": cells[1],
                        "object_type": cells[2] if cells[2] != "-" else None,
                        "object_key": cells[3] if cells[3] != "-" else None,
                        "preferred_action": cells[4],
                        "message": cells[5],
                    })

        return divergences

    def get_all_divergences(self) -> List[Dict]:
        """Combine aggregated and object divergences."""
        return self.aggregated_divergences + self.object_divergences

    def divergence_key(self, div: Dict) -> Tuple:
        """Generate unique key for divergence."""
        return (
            div.get("code"),
            div.get("object_type"),
            div.get("object_key"),
            div.get("scope") if "scope" in div else None,
        )


def compare_reports(old_report: ComplianceReport, new_report: ComplianceReport) -> Dict:
    """Compare two reports and identify changes."""
    old_divs = old_report.get_all_divergences()
    new_divs = new_report.get_all_divergences()

    old_keys = {old_report.divergence_key(d): d for d in old_divs}
    new_keys = {new_report.divergence_key(d): d for d in new_divs}

    # Find changes
    new_divergences = [
        new_keys[k] for k in new_keys if k not in old_keys
    ]
    resolved_divergences = [
        old_keys[k] for k in old_keys if k not in new_keys
    ]
    recurring_divergences = [
        new_keys[k] for k in new_keys if k in old_keys
    ]

    # Count by severity
    def count_by_severity(divs: List[Dict]) -> Dict[str, int]:
        counts = {}
        for div in divs:
            sev = div.get("severity", "unknown")
            counts[sev] = counts.get(sev, 0) + 1
        return counts

    return {
        "old_total": old_report.total_divergences,
        "new_total": new_report.total_divergences,
        "delta": new_report.total_divergences - old_report.total_divergences,
        "old_severity_counts": count_by_severity(old_divs),
        "new_severity_counts": count_by_severity(new_divs),
        "new_divergences": new_divergences,
        "resolved_divergences": resolved_divergences,
        "recurring_divergences": recurring_divergences,
        "old_report": old_report,
        "new_report": new_report,
    }


def render_comparison(comparison: Dict, device_name: str = None) -> str:
    """Render comparison report as Markdown."""
    old_report = comparison["old_report"]
    new_report = comparison["new_report"]

    if device_name is None:
        device_name = new_report.hostname or "unknown"

    lines = [
        f"# Comparativo de Compliance — {device_name}\n",
        "## 1. Resumo\n",
        f"- Relatório anterior: {old_report.filepath.name}\n",
        f"- Relatório novo: {new_report.filepath.name}\n",
        f"- Total anterior: {comparison['old_total']} divergências\n",
        f"- Total agora: {comparison['new_total']} divergências\n",
        f"- Delta: {comparison['delta']:+d}\n",
        f"- Status anterior: {old_report.status or 'não disponível'}\n",
        f"- Status agora: {new_report.status or 'não disponível'}\n",
        "\n## 2. Evolução por severidade\n",
    ]

    # Severity evolution table
    all_severities = set(
        list(comparison["old_severity_counts"].keys())
        + list(comparison["new_severity_counts"].keys())
    )
    all_severities = sorted(all_severities)

    lines.append("| Severidade | Antes | Agora | Delta |\n")
    lines.append("|---|---|---|---|\n")
    for sev in all_severities:
        before = comparison["old_severity_counts"].get(sev, 0)
        after = comparison["new_severity_counts"].get(sev, 0)
        delta = after - before
        lines.append(f"| {sev} | {before} | {after} | {delta:+d} |\n")

    # New divergences
    lines.append("\n## 3. Novas divergências\n")
    if comparison["new_divergences"]:
        lines.append(
            "| Severidade | Código | Tipo | Chave | Ação | Mensagem |\n"
        )
        lines.append("|---|---|---|---|---|---|\n")
        for div in comparison["new_divergences"]:
            lines.append(
                f"| {div.get('severity', '-')} | {div.get('code', '-')} | "
                f"{div.get('object_type', '-')} | {div.get('object_key', '-')} | "
                f"{div.get('preferred_action', '-')} | {div.get('message', '-')} |\n"
            )
    else:
        lines.append("Nenhuma divergência nova.\n")

    # Resolved divergences
    lines.append("\n## 4. Divergências resolvidas\n")
    if comparison["resolved_divergences"]:
        lines.append(
            "| Severidade | Código | Tipo | Chave | Ação | Mensagem |\n"
        )
        lines.append("|---|---|---|---|---|---|\n")
        for div in comparison["resolved_divergences"]:
            lines.append(
                f"| {div.get('severity', '-')} | {div.get('code', '-')} | "
                f"{div.get('object_type', '-')} | {div.get('object_key', '-')} | "
                f"{div.get('preferred_action', '-')} | {div.get('message', '-')} |\n"
            )
    else:
        lines.append("Nenhuma divergência resolvida.\n")

    # Recurring divergences
    lines.append("\n## 5. Divergências recorrentes (ainda não resolvidas)\n")
    if comparison["recurring_divergences"]:
        lines.append(
            "| Severidade | Código | Tipo | Chave | Ação | Mensagem |\n"
        )
        lines.append("|---|---|---|---|---|---|\n")
        for div in comparison["recurring_divergences"]:
            lines.append(
                f"| {div.get('severity', '-')} | {div.get('code', '-')} | "
                f"{div.get('object_type', '-')} | {div.get('object_key', '-')} | "
                f"{div.get('preferred_action', '-')} | {div.get('message', '-')} |\n"
            )
    else:
        lines.append("Nenhuma divergência recorrente.\n")

    # Observations
    lines.extend([
        "\n## 6. Observações\n",
        "- Comparação baseada em análise local de Markdown.\n",
        "- Nenhuma API real chamada.\n",
        "- Nenhum raw JSON utilizado.\n",
        "- Nenhuma escrita no NetBox.\n",
        "- Nenhuma alteração em equipamento.\n",
        "- Chave de divergência: (code, object_type, object_key, scope).\n",
    ])

    return "".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Compare two compliance reports"
    )
    parser.add_argument("--old", required=True, help="Older report .md file")
    parser.add_argument("--new", required=True, help="Newer report .md file")
    parser.add_argument("--output", help="Output comparison .md file")
    parser.add_argument(
        "--device", help="Device name (auto-detected if not provided)"
    )
    args = parser.parse_args()

    try:
        old_report = ComplianceReport(args.old)
        new_report = ComplianceReport(args.new)
    except FileNotFoundError as e:
        print(f"Error: report file not found: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error reading reports: {e}", file=sys.stderr)
        return 1

    comparison = compare_reports(old_report, new_report)
    output = render_comparison(comparison, args.device)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"✓ Comparison written to: {output_path}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
