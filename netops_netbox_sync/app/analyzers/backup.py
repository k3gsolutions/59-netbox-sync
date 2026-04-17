"""
Gerenciamento de backup versionado do running-config.

Salva o running-config com timestamp em backups/<hostname>/ e
calcula diff em relação ao backup anterior.

Estrutura em disco:
  backups/
    INFORR-BVA-JCL-RX/
      20260406_201500_INFORR-BVA-JCL-RX.txt
      20260407_030000_INFORR-BVA-JCL-RX.txt
      ...
"""
import difflib
import os
from datetime import datetime


_MAX_DIFF_LINES = 200   # limite de linhas de diff retornadas no resultado


def save_backup(hostname: str, running_config: str,
                backup_dir: str = "backups") -> dict:
    """
    Salva o running-config e compara com o backup anterior.

    Returns:
        {
            "file":          caminho do arquivo salvo,
            "previous_file": arquivo anterior (ou None),
            "lines_added":   int,
            "lines_removed": int,
            "changed":       bool,
            "diff":          list[str]  (primeiras N linhas do unified diff),
        }
    """
    # Garante diretório
    device_dir = os.path.join(backup_dir, hostname)
    os.makedirs(device_dir, exist_ok=True)

    # Lê backup anterior (último arquivo .txt no diretório)
    existing_files = sorted(
        f for f in os.listdir(device_dir) if f.endswith(".txt")
    )
    prev_content: str | None = None
    prev_file:    str | None = None
    if existing_files:
        prev_file = os.path.join(device_dir, existing_files[-1])
        with open(prev_file, encoding="utf-8", errors="replace") as fh:
            prev_content = fh.read()

    # Salva novo backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"{timestamp}_{hostname}.txt"
    filepath  = os.path.join(device_dir, filename)
    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write(running_config)

    # Calcula diff
    diff_lines: list[str] = []
    lines_added = lines_removed = 0

    if prev_content is not None:
        diff_lines = list(difflib.unified_diff(
            prev_content.splitlines(),
            running_config.splitlines(),
            fromfile=os.path.basename(prev_file),
            tofile=filename,
            lineterm="",
        ))
        lines_added   = sum(1 for l in diff_lines
                            if l.startswith("+") and not l.startswith("+++"))
        lines_removed = sum(1 for l in diff_lines
                            if l.startswith("-") and not l.startswith("---"))

    return {
        "file":          filepath,
        "previous_file": prev_file,
        "lines_added":   lines_added,
        "lines_removed": lines_removed,
        "changed":       (lines_added + lines_removed) > 0,
        "diff":          diff_lines[:_MAX_DIFF_LINES],
    }


def list_backups(hostname: str, backup_dir: str = "backups") -> list[dict]:
    """Lista todos os backups disponíveis para um hostname."""
    device_dir = os.path.join(backup_dir, hostname)
    if not os.path.isdir(device_dir):
        return []
    files = sorted(
        f for f in os.listdir(device_dir) if f.endswith(".txt")
    )
    return [
        {
            "file": os.path.join(device_dir, f),
            "timestamp": f.split("_")[0] + "_" + f.split("_")[1],
            "size_bytes": os.path.getsize(os.path.join(device_dir, f)),
        }
        for f in files
    ]
