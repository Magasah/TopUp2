from typing import Any

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.inline import admin_order_kb
from utils.admins import get_admin_ids


def _unified_order_kb(game_type: str, order_id: int, user_tg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Принять",
                    callback_data=f"order_accept_{game_type}_{order_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"order_reject_{game_type}_{order_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💬 Написать",
                    url=f"tg://user?id={user_tg_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=f"order_delete_{game_type}_{order_id}",
                )
            ],
        ]
    )


async def notify_admins_typed_order(
    bot: Bot,
    game_type: str,
    order: dict[str, Any],
    caption: str,
) -> None:
    receipt_id = order.get("receipt_file_id")
    oid = int(order["id"])
    uid = int(order["user_tg_id"])
    kb = _unified_order_kb(game_type, oid, uid)
    for aid in get_admin_ids():
        try:
            if receipt_id:
                await bot.send_photo(
                    aid,
                    receipt_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=kb,
                )
            else:
                await bot.send_message(
                    aid,
                    caption,
                    parse_mode="HTML",
                    reply_markup=kb,
                )
        except Exception:
            continue


async def notify_admins_new_order(
    bot: Bot,
    order: dict[str, Any],
    caption: str,
) -> None:
    receipt_id = order.get("receipt_file_id")
    for aid in get_admin_ids():
        try:
            if receipt_id:
                await bot.send_photo(
                    aid,
                    receipt_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=admin_order_kb(
                        int(order["id"]),
                        int(order["user_tg_id"]),
                    ),
                )
            else:
                await bot.send_message(
                    aid,
                    caption,
                    parse_mode="HTML",
                    reply_markup=admin_order_kb(
                        int(order["id"]),
                        int(order["user_tg_id"]),
                    ),
                )
        except Exception:
            continue


async def notify_user(bot: Bot, tg_id: int, text: str) -> None:
    try:
        await bot.send_message(tg_id, text, parse_mode="HTML")
    except Exception:
        pass
