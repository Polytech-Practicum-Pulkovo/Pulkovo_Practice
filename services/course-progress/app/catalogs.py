import os
from pathlib import Path

CATALOGS_DIR = Path(os.getenv("CATALOGS_DIR", "/app/catalogs"))


def list_catalog_files() -> list[str]:
    if not CATALOGS_DIR.exists():
        return []
    return sorted(p.name for p in CATALOGS_DIR.iterdir() if p.is_file())
