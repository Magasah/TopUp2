from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database import queries as db

router = Router()

TYPE_ICON = {
    "ff": "🔥",
    "br": "🚗",
    "steam": "🎮",
    "settings": "⚙️",
    "tickets": "🎰",
    "standoff": "🎯",
    "ai_sub": "🤖",
}
STATUS_TITLE = {"pending": "⏳ Новые", "accepted": "✅ Выполненные", "rejected": "❌ Отклонённые"}
PAGE_SIZE = 8

REJECT_REASON_CODES = ("pay", "gid", "stk", "oth")


class AdminOrderStates(StatesGroup):
    waiting_reject_reason = State()


def _reject_reason_key(code: str) -> str:
    return {
        "pay": "reject_reason_payment",
        "gid": "reject_reason_id",
        "stk": "reject_reason_stock",
    }.get(code, "reject_reason_other")


def _parse_typed_callback(data: str, prefix: str) -> tuple[str, int]:
    raw = data.removeprefix(prefix)
    game_type, oid = raw.rsplit("_", 1)
    return game_type, int(oid)


def _reject_reasons_kb(game_type: str, order_id: int, t) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=t("reject_reason_btn_payment"),
                callback_data=f"ordrej_{game_type}_{order_id}_pay",
            )
        ],
        [
            InlineKeyboardButton(
                text=t("reject_reason_btn_id"),
                callback_data=f"ordrej_{game_type}_{order_id}_gid",
            )
        ],
        [
            InlineKeyboardButton(
                text=t("reject_reason_btn_stock"),
                callback_data=f"ordrej_{game_type}_{order_id}_stk",
            )
        ],
        [
            InlineKeyboardButton(
                text=t("reject_reason_btn_other"),
                callback_data=f"ordrej_{game_type}_{order_id}_oth",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def get_order_by_type(game_type: str, order_id: int):
    if game_type == "ff":
        return await db.get_order(order_id)
    if game_type == "steam":
        return await db.get_steam_order(order_id)
    if game_type == "br":
        return await db.get_br_order(order_id)
    if game_type == "settings":
        return await db.get_settings_order(order_id)
    if game_type == "tickets":
        return await db.get_ticket_order(order_id)
    if game_type == "standoff":
        return await db.get_standoff_order(order_id)
    if game_type == "ai_sub":
        return await db.get_ai_sub_order(order_id)
    return None


async def _show_main(callback: CallbackQuery) -> None:
    counts = await db.get_all_orders_counts()
    new_count = counts["pending"]
    done_count = counts["accepted"]
    rej_count = counts["rejected"]
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"⏳ Новые заказы ({new_count})", callback_data="all_orders_new")],
            [InlineKeyboardButton(text="✅ Выполненные", callback_data="all_orders_done")],
            [InlineKeyboardButton(text="❌ Отклонённые", callback_data="all_orders_rejected")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="adm_back_panel")],
        ]
    )
    await callback.message.edit_text(
        "📋 ВСЕ ЗАКАЗЫ\n"
        "─────────────────────\n"
        f"⏳ Новых: {new_count}\n"
        f"✅ Выполнено: {done_count}\n"
        f"❌ Отклонено: {rej_count}",
        reply_markup=kb,
    )


def _status_cb_map(callback_data: str) -> str:
    if callback_data == "all_orders_new":
        return "pending"
    if callback_data == "all_orders_done":
        return "accepted"
    return "rejected"


async def _show_list(callback: CallbackQuery, status: str, page: int = 0) -> None:
    rows = await db.get_all_orders_paginated(status=status, page=page, limit=PAGE_SIZE)
    title = STATUS_TITLE[status]
    if not rows and page == 0:
        await callback.message.edit_text(
            f"{title}\n\nСписок пуст.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="◀️ К заказам", callback_data="admin_orders")]]
            ),
        )
        return

    kb_rows = []
    for order in rows:
        icon = TYPE_ICON.get(order["game_type"], "📦")
        username = f"@{order.get('username')}" if order.get("username") else f"id:{order['user_tg_id']}"
        kb_rows.append(
            [
                InlineKeyboardButton(
                    text=f"{icon} {username} | {order['item']} | {order['amount_str']}",
                    callback_data=f"view_order_{order['game_type']}_{order['id']}",
                )
            ]
        )
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀ Пред", callback_data=f"all_orders_page_{status}_{page - 1}"))
    if len(rows) == PAGE_SIZE:
        nav.append(InlineKeyboardButton(text="▶ След", callback_data=f"all_orders_page_{status}_{page + 1}"))
    if nav:
        kb_rows.append(nav)
    kb_rows.append([InlineKeyboardButton(text="◀️ К заказам", callback_data="admin_orders")])
    await callback.message.edit_text(f"{title}\nСтраница: {page + 1}", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))


@router.callback_query(F.data == "admin_orders")
async def admin_orders(callback: CallbackQuery) -> None:
    await callback.answer()
    await _show_main(callback)


@router.callback_query(F.data.in_(("all_orders_new", "all_orders_done", "all_orders_rejected")))
async def admin_orders_group(callback: CallbackQuery) -> None:
    await callback.answer()
    await _show_list(callback, _status_cb_map(callback.data), 0)


@router.callback_query(F.data.startswith("all_orders_page_"))
async def admin_orders_page(callback: CallbackQuery) -> None:
    await callback.answer()
    raw = callback.data.removeprefix("all_orders_page_")
    status, page_s = raw.rsplit("_", 1)
    await _show_list(callback, status, int(page_s))


@router.callback_query(F.data.startswith("view_order_"))
async def view_order(callback: CallbackQuery) -> None:
    await callback.answer()
    game_type, order_id = _parse_typed_callback(callback.data or "", "view_order_")
    order = await get_order_by_type(game_type, order_id)
    if not order:
        await callback.message.answer("Заказ не найден.")
        return

    if game_type == "ff":
        text = (
            f"🔥 Заказ Free Fire #{order_id}\n"
            "─────────────────────\n"
            f"👤 @{order.get('username') or order['user_tg_id']}\n"
            f"💎 {order.get('product_label')}\n"
            f"💰 {order.get('price_tjs')} смн | 💳 {order.get('payment_method')}\n"
            f"🆔 ID в игре: {order.get('game_account_id')}\n"
            f"🕐 {order.get('created_at')}"
        )
    elif game_type == "steam":
        text = (
            f"🎮 Заказ Steam #{order_id}\n"
            "─────────────────────\n"
            f"👤 @{order.get('username') or order['user_tg_id']}\n"
            f"👤 Steam: {order.get('steam_login')}\n"
            f"💵 {order.get('amount_usd')} USD → {order.get('amount_tjs')} смн\n"
            f"📈 Курс: {order.get('usd_rate')}\n"
            f"💳 {order.get('payment_method')}"
        )
    elif game_type == "br":
        text = (
            f"🚗 Заказ Black Russia #{order_id}\n"
            "─────────────────────\n"
            f"👤 @{order.get('username') or order['user_tg_id']}\n"
            f"🖥 Сервер: {order.get('server_name')}\n"
            f"👾 Ник: {order.get('nickname')}\n"
            f"💰 {order.get('amount')} ₽ | 💳 {order.get('payment_method')}"
        )
    elif game_type == "settings":
        order_type = str(order.get("order_type") or "")
        order_label = {
            "ff_settings_basic": "FF Настройки (обычные)",
            "ff_settings_vip": "FF Настройки (VIP)",
            "ff_vip_panel": "FF VIP Панель",
            "ff_panel_android": "FF Панель Android",
            "ff_panel_iphone": "FF Панель iPhone",
            "telegram_stars": "Telegram Stars",
            "telegram_premium": "Telegram Premium",
        }.get(order_type, order_type)
        target_label = "🎯 Получатель" if order_type.startswith("telegram_") else "📱 Телефон"
        text = (
            f"⚙️ Заказ услуги #{order_id}\n"
            "─────────────────────\n"
            f"👤 @{order.get('username') or order['user_tg_id']}\n"
            f"🧾 Тип: {order_label}\n"
            f"{target_label}: {order.get('phone_model')}\n"
            f"💰 {order.get('price_tjs')} смн | 💳 {order.get('payment_method')}\n"
            f"🕐 {order.get('created_at')}"
        )
    elif game_type == "standoff":
        text = (
            f"🎯 Standoff 2 #{order_id}\n"
            "─────────────────────\n"
            f"👤 @{order.get('username') or order['user_tg_id']}\n"
            f"📦 {order.get('product_label')}\n"
            f"💰 {order.get('price_tjs')} смн | 💳 {order.get('payment_method')}\n"
            f"🆔 ID: {order.get('game_account_id')}\n"
            f"🕐 {order.get('created_at')}"
        )
    elif game_type == "tickets":
        text = (
            f"🎰 Билеты #{order_id}\n"
            "─────────────────────\n"
            f"👤 @{order.get('username') or order['user_tg_id']}\n"
            f"🎫 {order.get('ticket_count')} шт.\n"
            f"💰 {order.get('price_tjs')} смн | 💳 {order.get('payment_method')}\n"
            f"🕐 {order.get('created_at')}"
        )
    elif game_type == "ai_sub":
        svc_key = str(order.get("service_key") or "")
        from handlers.ai_subscriptions import AI_SERVICES

        emoji = AI_SERVICES.get(svc_key, {}).get("emoji", "🤖")
        text = (
            f"🤖 ИИ подписка #{order_id}\n"
            "─────────────────────\n"
            f"👤 @{order.get('username') or order['user_tg_id']}\n"
            f"{emoji} {order.get('service_name')} — {order.get('plan_name')}\n"
            f"💵 {order.get('price_usd')} USD → {order.get('price_tjs')} смн\n"
            f"📈 Курс: {order.get('usd_rate')}\n"
            f"⏱ {order.get('period') or '1 месяц'}\n"
            f"💳 {order.get('payment_method')}\n"
            f"🕐 {order.get('created_at')}"
        )
    else:
        text = (
            f"📦 Заказ #{order_id}\n"
            "─────────────────────\n"
            f"👤 @{order.get('username') or order.get('user_tg_id')}\n"
            f"🧾 {order.get('item') or order.get('order_type') or '-'}\n"
            f"💳 {order.get('payment_method') or '-'}"
        )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять", callback_data=f"order_accept_{game_type}_{order_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"order_reject_{game_type}_{order_id}"),
            ],
            [InlineKeyboardButton(text="💬 Написать", url=f"tg://user?id={order['user_tg_id']}")],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"order_delete_{game_type}_{order_id}")],
            [InlineKeyboardButton(text="◀️ К списку", callback_data="admin_orders")],
        ]
    )
    receipt = order.get("receipt_file_id")
    if receipt:
        await callback.message.answer_photo(receipt, caption=text, reply_markup=kb)
    else:
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("order_accept_"))
async def order_accept(callback: CallbackQuery, t) -> None:
    await callback.answer()
    game_type, order_id = _parse_typed_callback(callback.data or "", "order_accept_")
    order = await get_order_by_type(game_type, order_id)
    if not order:
        await callback.message.answer("❌ Заказ не найден.")
        return
    await db.update_order_status_by_type(game_type, order_id, "accepted")
    order = await get_order_by_type(game_type, order_id)
    if not order:
        await callback.message.answer("❌ Заказ не найден после обновления.")
        return
    uid = int(order["user_tg_id"])
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    if game_type == "ai_sub":
        svc_key = str(order.get("service_key") or "")
        from handlers.ai_subscriptions import AI_SERVICES

        svc = AI_SERVICES.get(svc_key, {})
        await callback.bot.send_message(
            uid,
            t(
                "ai_sub_activated",
                emoji=svc.get("emoji", "🤖"),
                service=order.get("service_name") or svc.get("name", ""),
                plan=order.get("plan_name") or "",
            ),
            parse_mode="HTML",
        )
    else:
        await callback.bot.send_message(uid, t("order_accepted_user", oid=order_id), parse_mode="HTML")
    await callback.message.answer(f"✅ Заказ #{order_id} ({game_type}) принят, пользователь уведомлён.")


@router.callback_query(F.data.startswith("order_reject_"))
async def order_reject_start(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    game_type, oid = _parse_typed_callback(callback.data or "", "order_reject_")
    await callback.message.answer(
        t("reject_pick_reason"),
        reply_markup=_reject_reasons_kb(game_type, oid, t),
    )


@router.callback_query(F.data.startswith("ordrej_"))
async def order_reject_picked(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    rest = (callback.data or "").removeprefix("ordrej_")
    game_type, oid_s, code = rest.split("_", 2)
    order_id = int(oid_s)
    if code == "oth":
        await state.set_state(AdminOrderStates.waiting_reject_reason)
        await state.update_data(game_type=game_type, order_id=order_id)
        await callback.message.answer(t("reject_enter_custom_reason"))
        return
    reason = t(_reject_reason_key(code))
    order = await get_order_by_type(game_type, order_id)
    if not order:
        return
    await db.update_order_status_by_type(game_type, order_id, "rejected")
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    uid = int(order["user_tg_id"])
    if game_type == "ai_sub":
        await callback.bot.send_message(
            uid,
            t("ai_sub_rejected", id=order_id, reason=reason),
            parse_mode="HTML",
        )
    else:
        await callback.bot.send_message(
            uid,
            t("order_rejected_with_reason", oid=order_id, reason=reason),
            parse_mode="HTML",
        )
    await callback.message.answer("❌ Статус: отклонён.")


@router.message(StateFilter(AdminOrderStates.waiting_reject_reason), F.text)
async def order_reject_custom_finish(message: Message, state: FSMContext, t) -> None:
    data = await state.get_data()
    game_type = str(data["game_type"])
    order_id = int(data["order_id"])
    reason = (message.text or "").strip()
    order = await get_order_by_type(game_type, order_id)
    await state.clear()
    if not order:
        return
    await db.update_order_status_by_type(game_type, order_id, "rejected")
    uid = int(order["user_tg_id"])
    if game_type == "ai_sub":
        await message.bot.send_message(
            uid,
            t("ai_sub_rejected", id=order_id, reason=reason),
            parse_mode="HTML",
        )
    else:
        await message.bot.send_message(
            uid,
            t("order_rejected_with_reason", oid=order_id, reason=reason),
            parse_mode="HTML",
        )
    await message.answer("❌ Статус: отклонён.")


@router.callback_query(F.data.startswith("order_delete_"))
async def order_delete(callback: CallbackQuery) -> None:
    await callback.answer()
    game_type, order_id = _parse_typed_callback(callback.data or "", "order_delete_")
    if game_type == "ff":
        await db.delete_order(order_id)
    elif game_type == "steam":
        await db.delete_steam_order(order_id)
    elif game_type == "br":
        await db.delete_br_order(order_id)
    elif game_type == "settings":
        await db.delete_settings_order(order_id)
    elif game_type == "tickets":
        await db.delete_roulette_ticket_order(order_id)
    elif game_type == "standoff":
        await db.delete_standoff_order(order_id)
    elif game_type == "ai_sub":
        await db.delete_ai_sub_order(order_id)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer("🗑 Заказ удалён.")

# ✅ ГОТОВО: handlers/admin/all_orders.py
