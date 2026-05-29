"""Бонусная система удалена.

Функция оставлена как no-op для обратной совместимости с местами, которые
её всё ещё импортируют, чтобы не было ошибок импорта. Никаких бонусов не
начисляется и пользователю ничего не отправляется.
"""

from typing import Callable

from aiogram import Bot


async def check_and_grant_bonus(
    bot: Bot,
    user_tg_id: int,
    t: Callable[..., str],
) -> None:
    return None
