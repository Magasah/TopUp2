import math
from typing import Optional

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from database.queries import (
    count_all_orders,
    count_orders_by_status,
    delete_order,
    get_order_by_id,
    get_orders_by_status,
    update_order_status,
)
from utils.formatter import order_to_card
from utils.notify import notify_user

router = Router()

PAGE_SIZE = 10


def _orders_menu_kb(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("orders_pending"),
                    callback_data="adm_ordcat_pending",
                ),
                InlineKeyboardButton(
                    text=t("orders_accepted"),
                    callback_data="adm_ordcat_accepted",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("orders_rejected"),
                    callback_data="adm_ordcat_rejected",
                ),
                InlineKeyboardButton(
                    text=t("orders_all"),
                    callback_data="adm_ordcat_all",
                ),
            ],
            [InlineKeyboardButton(text=t("back"), callback_data="adm_back_panel")],
        ]
    )


@router.callback_query(F.data == "adm_orders_menu")
async def orders_menu(callback: CallbackQuery, t) -> None:
    await callback.answer()
    await callback.message.edit_text(
        t("orders_filter"),
        reply_markup=_orders_menu_kb(t),
        parse_mode=ParseMode.HTML,
    )


def _status_from_cat(cat: str) -> Optional[str]:
    return None if cat == "all" else cat


async def _render_order_list(
    callback: CallbackQuery,
    t,
    cat: str,
    page: int,
) -> None:
    st = _status_from_cat(cat)
    if st:
        total = await count_orders_by_status(st)
    else:
        total = await count_all_orders()
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))
    offset = page * PAGE_SIZE
    rows = await get_orders_by_status(st, limit=PAGE_SIZE, offset=offset)
    if not rows:
        kb_rows: list[list[InlineKeyboardButton]] = [
            [InlineKeyboardButton(text=t("back"), callback_data="adm_orders_menu")]
        ]
        await callback.message.edit_text(
            t("orders_empty"),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
            parse_mode=ParseMode.HTML,
        )
        return
    header = f"{t('orders_filter')}\n<code>{cat}</code> · {page + 1}/{total_pages}\n"
    lines = [header]
    kb_rows = []
    for o in rows:
        uname = o.get("username") or str(o["user_tg_id"])
        lines.append(f"#{o['id']} · @{uname} · {o['status']}")
        kb_rows.append(
            [
                InlineKeyboardButton(
                    text=f"#{o['id']}",
                    callback_data=f"adm_order_view_{o['id']}",
                )
            ]
        )
    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text=t("page_prev"),
                callback_data=f"adm_ordpage_{cat}_{page - 1}",
            )
        )
    if page < total_pages - 1:
        nav.append(
            InlineKeyboardButton(
                text=t("page_next"),
                callback_data=f"adm_ordpage_{cat}_{page + 1}",
            )
        )
    if nav:
        kb_rows.append(nav)
    kb_rows.append(
        [InlineKeyboardButton(text=t("back"), callback_data="adm_orders_menu")]
    )
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data.startswith("adm_ordcat_"))
async def orders_category(callback: CallbackQuery, t) -> None:
    await callback.answer()
    cat = (callback.data or "").removeprefix("adm_ordcat_")
    await _render_order_list(callback, t, cat, 0)


@router.callback_query(F.data.startswith("adm_ordpage_"))
async def orders_page(callback: CallbackQuery, t) -> None:
    await callback.answer()
    raw = (callback.data or "").removeprefix("adm_ordpage_")
    cat, page_s = raw.rsplit("_", 1)
    await _render_order_list(callback, t, cat, int(page_s))


def _order_action_kb(oid: int, user_tg_id: int, status: str, t) -> InlineKeyboardMarkup:
    row1: list[InlineKeyboardButton] = []
    if status == "pending":
        row1 = [
            InlineKeyboardButton(
                text=t("accept"),
                callback_data=f"accept_{oid}",
            ),
            InlineKeyboardButton(
                text=t("reject"),
                callback_data=f"reject_{oid}",
            ),
        ]
    rows: list[list[InlineKeyboardButton]] = []
    if row1:
        rows.append(row1)
    rows.append(
        [
            InlineKeyboardButton(
                text=t("write_buyer"),
                url=f"tg://user?id={user_tg_id}",
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=t("admin_order_delete"),
                callback_data=f"del_order_{oid}",
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=t("back"),
                callback_data="adm_orders_menu",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("adm_order_view_"))
async def order_view(callback: CallbackQuery, t) -> None:
    await callback.answer()
    oid = int((callback.data or "").removeprefix("adm_order_view_"))
    order = await get_order_by_id(oid)
    if not order:
        return
    cap = order_to_card(order, t)
    rid = order.get("receipt_file_id")
    kb = _order_action_kb(
        oid,
        int(order["user_tg_id"]),
        str(order.get("status") or ""),
        t,
    )
    if rid:
        await callback.message.answer_photo(rid, caption=cap, reply_markup=kb)
    else:
        await callback.message.answer(cap, reply_markup=kb)


@router.callback_query(F.data.startswith("accept_"))
async def order_accept(callback: CallbackQuery, t) -> None:
    oid = int((callback.data or "").removeprefix("accept_"))
    await update_order_status(oid, "accepted", completed=True)
    order = await get_order_by_id(oid)
    await callback.answer(t("accept"))
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    if order:
        await notify_user(
            callback.bot,
            int(order["user_tg_id"]),
            t("order_accepted_user", oid=oid),
        )


@router.callback_query(F.data.startswith("reject_"))
async def order_reject(callback: CallbackQuery, t) -> None:
    oid = int((callback.data or "").removeprefix("reject_"))
    await update_order_status(oid, "rejected", completed=True)
    order = await get_order_by_id(oid)
    await callback.answer(t("reject"))
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    if order:
        await notify_user(
            callback.bot,
            int(order["user_tg_id"]),
            t("order_rejected_user", oid=oid),
        )


@router.callback_query(F.data.startswith("del_order_"))
async def delete_order_confirm(callback: CallbackQuery, t) -> None:
    await callback.answer()
    oid = int((callback.data or "").removeprefix("del_order_"))
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("admin_delete_yes"),
                    callback_data=f"confirm_del_{oid}",
                ),
                InlineKeyboardButton(
                    text=t("admin_delete_cancel"),
                    callback_data=f"adm_order_view_{oid}",
                ),
            ],
        ]
    )
    await callback.message.answer(
        t("admin_delete_confirm", oid=oid),
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("confirm_del_"))
async def delete_order_execute(callback: CallbackQuery, t) -> None:
    await callback.answer()
    oid = int((callback.data or "").removeprefix("confirm_del_"))
    await delete_order(oid)
    chat_id = callback.from_user.id
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.bot.send_message(chat_id, t("admin_order_deleted"))

# ✅ ГОТОВО: handlers/admin/orders.py
