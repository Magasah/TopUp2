from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database.queries import (
    delete_settings_order,
    get_settings_order,
    get_settings_orders_by_status,
    update_settings_order_status,
    update_settings_order_text,
    update_vip_file,
)
from utils.formatter import fmt_price, payment_label

router = Router()


class AdminSettingsStates(StatesGroup):
    waiting_settings_text = State()
    waiting_vip_file = State()


def _filters_kb(prefix: str, t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("orders_new"), callback_data=f"{prefix}_pending"),
                InlineKeyboardButton(text=t("orders_done"), callback_data=f"{prefix}_accepted"),
                InlineKeyboardButton(text=t("orders_declined"), callback_data=f"{prefix}_rejected"),
            ],
            [InlineKeyboardButton(text=t("back"), callback_data="adm_back_panel")],
        ]
    )


@router.callback_query(F.data == "adm_settings_orders")
async def settings_orders_menu(callback: CallbackQuery, t) -> None:
    await callback.answer()
    await callback.message.answer(t("adm_ff_settings_orders"), reply_markup=_filters_kb("sord", t))


@router.callback_query(F.data == "adm_vip_orders")
async def vip_orders_menu(callback: CallbackQuery, t) -> None:
    await callback.answer()
    await callback.message.answer(t("adm_ff_vip_orders"), reply_markup=_filters_kb("vord", t))


async def _show_list(callback: CallbackQuery, t, status: str, target_type: str) -> None:
    rows = await get_settings_orders_by_status(status)
    rows = [r for r in rows if r.get("order_type") == target_type]
    if not rows:
        await callback.message.answer(t("orders_empty"))
        return
    kb_rows = [[InlineKeyboardButton(text=f"#{r['id']}", callback_data=f"sord_view_{r['id']}")] for r in rows]
    await callback.message.answer("Список заказов:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))


@router.callback_query(F.data.in_(("sord_pending", "sord_accepted", "sord_rejected")))
async def settings_orders_filter(callback: CallbackQuery, t) -> None:
    await callback.answer()
    status = callback.data.removeprefix("sord_")
    await _show_list(callback, t, status, "ff_settings_basic")
    await _show_list(callback, t, status, "ff_settings_vip")


@router.callback_query(F.data.in_(("vord_pending", "vord_accepted", "vord_rejected")))
async def vip_orders_filter(callback: CallbackQuery, t) -> None:
    await callback.answer()
    status = callback.data.removeprefix("vord_")
    await _show_list(callback, t, status, "ff_vip_panel")


@router.callback_query(F.data.startswith("sord_view_"))
async def settings_order_view(callback: CallbackQuery, t) -> None:
    await callback.answer()
    oid = int(callback.data.removeprefix("sord_view_"))
    order = await get_settings_order(oid)
    if not order:
        return
    order_type = str(order.get("order_type") or "")
    is_vip_panel = order_type == "ff_vip_panel"
    is_ff_settings = order_type in ("ff_settings_basic", "ff_settings_vip")
    can_send_payload = is_vip_panel or is_ff_settings
    send_btn = t("send_vip_btn") if is_vip_panel else t("send_settings_btn")
    send_cb = f"send_vip_{oid}" if is_vip_panel else f"send_settings_{oid}"
    text = (
        f"#{oid}\n"
        f"👤 @{order.get('username') or order.get('user_tg_id')}\n"
        f"⚙️ {order.get('order_type')}\n"
        f"📱 {order.get('phone_model')}\n"
        f"💰 {fmt_price(order.get('price_tjs'))}\n"
        f"💳 {payment_label(str(order.get('payment_method') or ''))}"
    )
    rows = [
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"sord_accept_{oid}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"sord_reject_{oid}"),
        ]
    ]
    if can_send_payload:
        rows.append([InlineKeyboardButton(text=send_btn, callback_data=send_cb)])
    rows.append([InlineKeyboardButton(text="💬 Написать покупателю", url=f"tg://user?id={order['user_tg_id']}")])
    rows.append([InlineKeyboardButton(text=t("delete_order_btn"), callback_data=f"sord_del_{oid}")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    if order.get("receipt_file_id"):
        await callback.message.answer_photo(order["receipt_file_id"], caption=text, reply_markup=kb)
    else:
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("sord_accept_"))
async def sord_accept(callback: CallbackQuery, t) -> None:
    await callback.answer()
    oid = int(callback.data.removeprefix("sord_accept_"))
    await update_settings_order_status(oid, "accepted")
    order = await get_settings_order(oid)
    if order:
        uid = int(order["user_tg_id"])
        await callback.bot.send_message(uid, f"✅ Ваш заказ #{oid} принят.")


@router.callback_query(F.data.startswith("sord_reject_"))
async def sord_reject(callback: CallbackQuery) -> None:
    await callback.answer()
    oid = int(callback.data.removeprefix("sord_reject_"))
    await update_settings_order_status(oid, "rejected")


@router.callback_query(F.data.startswith("sord_del_"))
async def sord_del(callback: CallbackQuery, t) -> None:
    await callback.answer()
    oid = int(callback.data.removeprefix("sord_del_"))
    await delete_settings_order(oid)
    await callback.message.answer(t("admin_order_deleted"))


@router.callback_query(F.data.startswith("send_settings_"))
async def send_settings_start(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    oid = int(callback.data.removeprefix("send_settings_"))
    await state.set_state(AdminSettingsStates.waiting_settings_text)
    await state.update_data(settings_order_id=oid)
    await callback.message.answer(t("admin_enter_settings_text"))


@router.message(AdminSettingsStates.waiting_settings_text, F.text)
async def send_settings_finish(message: Message, state: FSMContext, t) -> None:
    data = await state.get_data()
    oid = int(data.get("settings_order_id") or 0)
    text = (message.text or "").strip()
    order = await get_settings_order(oid)
    if not order:
        await state.clear()
        return
    await update_settings_order_text(oid, text)
    await update_settings_order_status(oid, "accepted")
    uid = int(order["user_tg_id"])
    await message.bot.send_message(uid, t("ff_settings_sent", text=text))
    await state.clear()
    await message.answer(t("settings_sent_confirm"))


@router.callback_query(F.data.startswith("send_vip_"))
async def send_vip_start(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    oid = int(callback.data.removeprefix("send_vip_"))
    await state.set_state(AdminSettingsStates.waiting_vip_file)
    await state.update_data(settings_order_id=oid)
    await callback.message.answer(t("admin_send_vip_file"))


@router.message(AdminSettingsStates.waiting_vip_file, F.document)
async def send_vip_finish(message: Message, state: FSMContext, t) -> None:
    data = await state.get_data()
    oid = int(data.get("settings_order_id") or 0)
    order = await get_settings_order(oid)
    if not order:
        await state.clear()
        return
    file_id = message.document.file_id
    await update_vip_file(oid, file_id)
    await update_settings_order_status(oid, "accepted")
    uid = int(order["user_tg_id"])
    await message.bot.send_message(uid, t("ff_vip_sent"))
    await message.bot.send_document(uid, file_id)
    await state.clear()
    await message.answer(t("vip_sent_confirm"))
