import os
from pathlib import Path

CATALOGS_DIR = Path(os.getenv("CATALOGS_DIR", "/app/catalogs"))


def list_catalog_files() -> list[str]:
    """Возвращает список доступных файлов каталога."""

    if not CATALOGS_DIR.exists():
        return []
    return sorted(p.name for p in CATALOGS_DIR.iterdir() if p.is_file())


def read_catalog_file(name: str) -> str:
    """Читает каталог по имени и защищает от выхода за пределы директории."""

    path = CATALOGS_DIR / name
    if not path.is_file() or CATALOGS_DIR not in path.resolve().parents:
        raise FileNotFoundError(name)
    return path.read_text(encoding="utf-8")
