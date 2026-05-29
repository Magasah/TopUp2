from collections.abc import Callable
from typing import Any

from aiogram.types import Message

from database import queries as db


async def check_receipt(message: Message, order_type: str, t: Callable[..., str]) -> tuple[bool, str]:
    """
    Проверяет фото чека на дублирование.
    Возвращает: (is_duplicate, error_text)
    """
    if not message.photo:
        return False, ""

    photo = message.photo[-1]
    existing = await db.is_receipt_duplicate(photo.file_unique_id)
    if not existing:
        return False, ""

    prev_id = existing.get("order_id")
    prev_type = existing.get("order_type") or order_type
    prev_date = str(existing.get("created_at") or "")[:16]
    return True, t(
        "receipt_duplicate",
        order_id=prev_id,
        date=prev_date,
        order_type=prev_type,
    )


async def register_receipt(
    file_unique_id: str,
    file_id: str,
    user_tg_id: int,
    order_type: str,
    order_id: int,
) -> None:
    await db.save_receipt_hash(
        file_unique_id,
        file_id,
        user_tg_id,
        order_type,
        order_id,
    )


def receipt_admin_note(t: Callable[..., str]) -> str:
    """Строка для подписи админу под фото чека."""
    return t("receipt_unique")


def append_receipt_note(caption: str, t: Callable[..., str]) -> str:
    note = receipt_admin_note(t)
    if note in caption:
        return caption
    return f"{caption}\n\n{note}"

# ✅ ГОТОВО: utils/receipt_checker.py
