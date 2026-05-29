from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import config
from database import queries as db
from utils import tg_api
from utils.receipt_checker import append_receipt_note, check_receipt, register_receipt
from utils.formatter import fmt_price
from utils.payment_flow import show_payment_methods, show_requisites

router = Router()

FF_VIP_PANEL_PRICE = 48.0


class VIPStates(StatesGroup):
    waiting_phone_model = State()
    waiting_confirm = State()
    waiting_payment_method = State()
    waiting_receipt = State()


@router.callback_query(F.data == "ff_vip")
async def ff_vip_open(callback: CallbackQuery, t) -> None:
    await callback.answer()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("ff_vip_buy_btn", price=fmt_price(FF_VIP_PANEL_PRICE)), callback_data="ffv_buy")],
            [InlineKeyboardButton(text=t("back"), callback_data="ff_choose_category")],
        ]
    )
    await callback.message.answer(t("ff_vip_panel_welcome", price=fmt_price(FF_VIP_PANEL_PRICE)), reply_markup=kb)


@router.callback_query(F.data == "ffv_buy")
async def ff_vip_buy(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    await state.set_state(VIPStates.waiting_phone_model)
    await state.update_data(order_type="ff_vip_panel", price=FF_VIP_PANEL_PRICE)
    await callback.message.answer(t("ff_enter_phone"))


@router.message(StateFilter(VIPStates.waiting_phone_model), F.text)
async def ff_vip_phone(message: Message, state: FSMContext, t) -> None:
    phone = (message.text or "").strip()
    if len(phone) < 5 or phone.isdigit():
        await message.answer(t("ff_invalid_phone"))
        return
    await state.update_data(phone_model=phone)
    await state.set_state(VIPStates.waiting_confirm)
    await message.answer(
        t(
            "ff_vip_summary",
            name=message.from_user.full_name,
            username=message.from_user.username or "нет",
            phone=phone,
            price=fmt_price(FF_VIP_PANEL_PRICE),
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=t("confirm_yes"), callback_data="ffv_confirm")],
                [InlineKeyboardButton(text=t("confirm_no"), callback_data="ffv_cancel")],
            ]
        ),
    )


@router.callback_query(F.data == "ffv_cancel", StateFilter("*"))
async def ff_vip_cancel(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    cur = await state.get_state()
    if cur and cur.startswith("VIPStates:"):
        await state.clear()
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(t("order_cancelled"))


@router.callback_query(F.data == "ffv_confirm", StateFilter(VIPStates.waiting_confirm))
async def ff_vip_go_payment(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    await show_payment_methods(callback.from_user.id, str(data["price"]), "смн")
    await state.set_state(VIPStates.waiting_payment_method)


@router.callback_query(
    F.data.in_(["pay_dc", "pay_alif"]),
    StateFilter(VIPStates.waiting_payment_method),
)
async def ff_vip_payment_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    await state.update_data(payment_method=callback.data)
    await show_requisites(callback.from_user.id, callback.data, str(data["price"]), "смн")
    await state.set_state(VIPStates.waiting_receipt)
    await callback.message.answer(
        "📸 Отправьте скриншот чека (фото). Если передумали, нажмите «Отменить оплату»."
    )
    try:
        await callback.message.delete()
    except Exception:
        pass


@router.message(StateFilter(VIPStates.waiting_receipt), F.photo)
async def ff_vip_receipt(message: Message, state: FSMContext, bot, t) -> None:
    is_dup, dup_text = await check_receipt(message, "settings", t)
    if is_dup:
        await message.answer(dup_text, parse_mode="HTML")
        return

    data = await state.get_data()
    photo = message.photo[-1]
    photo_id = photo.file_id
    order_id = await db.create_settings_order(
        user_tg_id=message.from_user.id,
        username=message.from_user.username or "",
        order_type="ff_vip_panel",
        phone_model=data.get("phone_model"),
        price_tjs=float(data.get("price") or 0),
        payment_method=data.get("payment_method"),
        receipt_file_id=photo_id,
    )
    await register_receipt(
        photo.file_unique_id, photo_id, message.from_user.id, "settings", order_id
    )
    await state.clear()
    await message.answer(t("order_created", oid=order_id))
    admin_text = (
        f"⚙️ НОВЫЙ ЗАКАЗ — 👑 Панель VIP FF #{order_id}\n"
        "───────────────────────\n"
        f"👤 {message.from_user.full_name}\n"
        f"📱 @{message.from_user.username or 'нет'}\n"
        f"📱 Телефон: {data.get('phone_model')}\n"
        f"💰 {data.get('price')} смн\n"
        f"💳 {data.get('payment_method')}"
    )
    admin_text = append_receipt_note(admin_text, t)
    admin_kb = {
        "inline_keyboard": [
            [
                {"text": "✅ Принять", "callback_data": f"order_accept_settings_{order_id}", "style": "success"},
                {"text": "❌ Отклонить", "callback_data": f"order_reject_settings_{order_id}", "style": "danger"},
            ],
            [{"text": "📤 Отправить настройки/файл", "callback_data": f"send_vip_{order_id}", "style": "primary"}],
            [{"text": "💬 Написать", "url": f"tg://user?id={message.from_user.id}"}],
            [{"text": "🗑 Удалить", "callback_data": f"order_delete_settings_{order_id}", "style": "danger"}],
        ]
    }
    for admin_id in config.admin_ids_list:
        try:
            await bot.send_photo(admin_id, photo_id, caption=admin_text, parse_mode="HTML")
            await tg_api.send_message(admin_id, "Действие:", admin_kb)
        except Exception:
            pass


@router.message(StateFilter(VIPStates.waiting_receipt), ~F.photo)
async def ff_vip_wrong_receipt(message: Message, t) -> None:
    await message.answer(t("receipt_need_photo"))

# ✅ ГОТОВО: handlers/ff_vip.py
