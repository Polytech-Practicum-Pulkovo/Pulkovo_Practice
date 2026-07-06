import os
import re
import subprocess
import tempfile
from pathlib import Path


def extract_text_from_pdf(pdf_path: str | os.PathLike) -> str:
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(path)

    if not _has_command("pdftotext"):
        raise RuntimeError("pdftotext not installed")

    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = Path(tmp_dir) / "extracted.txt"
        result = subprocess.run(
            ["pdftotext", str(path), str(output_path)],
            capture_output=True,
            check=False,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.decode("utf-8", errors="ignore"))
        return output_path.read_text(encoding="utf-8", errors="ignore")


def _has_command(command: str) -> bool:
    try:
        subprocess.run([command, "-v"], capture_output=True, check=False)
    except FileNotFoundError:
        return False
    return True
