"""Единый источник правды по администраторам.

Админы бывают двух видов:
- «супер-админы» из .env (ADMIN_IDS) — их нельзя удалить через панель;
- динамические админы из таблицы БД `admins` — их можно добавлять/удалять в панели.

Чтобы middlewares могли проверять права синхронно на каждом апдейте без обращения
к БД, актуальный набор ID держится в памяти и обновляется на старте и после изменений.
"""

from typing import Iterable

from config import config

_env_admin_ids: frozenset[int] = frozenset(config.admin_ids_list)
_admin_ids: set[int] = set(_env_admin_ids)


def is_super_admin(uid: int | None) -> bool:
    """Админ из .env — защищён от удаления через панель."""
    return uid is not None and uid in _env_admin_ids


def is_admin(uid: int | None) -> bool:
    return uid is not None and uid in _admin_ids


def get_admin_ids() -> list[int]:
    return sorted(_admin_ids)


def get_super_admin_ids() -> list[int]:
    return sorted(_env_admin_ids)


def _apply_db_admins(db_ids: Iterable[int]) -> None:
    _admin_ids.clear()
    _admin_ids.update(_env_admin_ids)
    _admin_ids.update(int(x) for x in db_ids)


async def refresh_admins_cache() -> None:
    """Перечитать динамических админов из БД и обновить кэш в памяти."""
    from database.queries import get_db_admin_ids

    db_ids = await get_db_admin_ids()
    _apply_db_admins(db_ids)
