from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import config
from database.queries import (
    count_recent_orders_for_user,
    create_order,
    get_all_games,
    get_order_by_id,
)
from keyboards.inline import main_menu_kb, payment_kb, receipt_cancel_markup
from utils.formatter import order_to_card
from utils.notify import notify_admins_new_order
from utils.receipt_checker import append_receipt_note, check_receipt, register_receipt
from utils.tg_api import send_message, send_photo
from utils.payment_flow import show_requisites

from handlers.order_flow import OrderFlow

router = Router()

MAX_ORDERS_PER_HOUR = 3


@router.callback_query(StateFilter("*"), F.data == "cancel_payment")
async def cancel_payment_any_state(
    callback: CallbackQuery,
    state: FSMContext,
    t,
) -> None:
    await callback.answer()
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    games = await get_all_games()
    await send_photo(
        callback.message.chat.id,
        config.welcome_photo,
        t("welcome", name=callback.from_user.first_name or ""),
        main_menu_kb(games, t),
    )


@router.callback_query(OrderFlow.waiting_receipt, F.data == "cancel_order_flow")
async def cancel_flow(
    callback: CallbackQuery,
    state: FSMContext,
    t,
) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.answer(t("order_cancelled"))


@router.callback_query(
    OrderFlow.waiting_receipt,
    F.data.in_(("pay_dc", "pay_alif")),
)
async def pick_payment(
    callback: CallbackQuery,
    state: FSMContext,
    t,
) -> None:
    await callback.answer()
    data = await state.get_data()
    if data.get("payment_method"):
        return

    key = callback.data or ""
    if key == "pay_alif":
        method = "alif"
        method_key = "pay_alif"
    else:
        method = "dc"
        method_key = "pay_dc"

    await state.update_data(payment_method=method)
    await show_requisites(
        callback.from_user.id,
        method_key,
        str(float(data.get("price_tjs") or 0)),
        "смн",
    )
    await callback.message.answer(
        t("receipt_wait_photo"),
        reply_markup=receipt_cancel_markup(t),
    )


@router.message(OrderFlow.waiting_receipt, F.photo)
async def receipt_photo(
    message: Message,
    state: FSMContext,
    t,
) -> None:
    data = await state.get_data()
    if not data.get("payment_method"):
        await send_message(
            message.chat.id,
            t("payment_title"),
            payment_kb(t),
        )
        return

    uid = message.from_user.id
    if await count_recent_orders_for_user(uid) >= MAX_ORDERS_PER_HOUR:
        await message.answer(t("order_rate_limit"))
        await state.clear()
        return

    is_dup, dup_text = await check_receipt(message, "ff", t)
    if is_dup:
        await message.answer(dup_text, reply_markup=receipt_cancel_markup(t), parse_mode="HTML")
        return

    photo = message.photo[-1]
    file_id = photo.file_id
    oid = await create_order(
        user_tg_id=uid,
        username=message.from_user.username,
        game_name=str(data.get("game_name") or ""),
        product_label=str(data.get("product_label") or ""),
        price_tjs=float(data.get("price_tjs") or 0),
        game_account_id=str(data.get("game_account_id") or ""),
        payment_method=str(data.get("payment_method") or ""),
        receipt_file_id=file_id,
        status="pending",
    )
    await register_receipt(photo.file_unique_id, file_id, uid, "ff", oid)
    order = await get_order_by_id(oid)
    await state.clear()
    await message.answer(t("order_created", oid=oid))
    if order:
        cap = append_receipt_note(order_to_card(order, t), t)
        await notify_admins_new_order(message.bot, order, cap)


@router.message(OrderFlow.waiting_receipt, F.text)
async def receipt_not_photo(message: Message, t) -> None:
    await message.answer(t("receipt_need_photo"))

# ✅ ГОТОВО: handlers/payment.py
