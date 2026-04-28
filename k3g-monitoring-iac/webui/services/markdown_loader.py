"""Markdown loader for read-only web UI."""

from pathlib import Path
from typing import Optional


def load_markdown(path: Path) -> Optional[str]:
    """Load markdown file content."""
    if not path.exists():
        return None

    if path.suffix != ".md":
        return None

    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return None


def render_markdown(content: str) -> str:
    """
    Render markdown to HTML.

    Try to use markdown library, fallback to escape + pre if not available.
    """
    try:
        import markdown
        return markdown.markdown(content, extensions=["tables", "fenced_code"])
    except ImportError:
        # Fallback: escape HTML and use <pre>
        import html
        escaped = html.escape(content)
        return f"<pre class='markdown-fallback'>{escaped}</pre>"


def extract_summary(content: str, max_lines: int = 5) -> str:
    """Extract first few lines as summary."""
    lines = content.split("\n")
    summary_lines = [line for line in lines[:max_lines] if line.strip()]
    return " ".join(summary_lines)[:200] + "..."


def load_json(path: Path) -> Optional[dict]:
    """Load JSON file."""
    if not path.exists():
        return None

    if path.suffix != ".json":
        return None

    try:
        import json
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
