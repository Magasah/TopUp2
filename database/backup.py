"""Резервное копирование SQLite при старте бота (заказы, товары, статистика)."""
import logging
import shutil
from datetime import datetime
from pathlib import Path

from database.db import get_db_path

_BACKUP_DIR = get_db_path().parent / "backups"
_MAX_BACKUPS = 10


def backup_database() -> None:
    src = get_db_path()
    if not src.is_file():
        return
    try:
        _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = _BACKUP_DIR / f"bot_{stamp}.db"
        shutil.copy2(src, dst)
        backups = sorted(_BACKUP_DIR.glob("bot_*.db"), key=lambda p: p.stat().st_mtime)
        for old in backups[:-_MAX_BACKUPS]:
            try:
                old.unlink()
            except OSError:
                pass
        logging.info("Резервная копия БД: %s", dst.name)
    except Exception as exc:
        logging.warning("Не удалось создать бэкап БД: %s", exc)
