from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import config
from database import queries as db
from utils import tg_api
from utils.formatter import fmt_price
from utils.receipt_checker import append_receipt_note, check_receipt, register_receipt
from utils.payment_flow import show_payment_methods, show_requisites

router = Router()

FF_BASIC_PRICE = 10.0
FF_VIP_SETTINGS_PRICE = 20.0
FF_PANEL_ANDROID_PRICE = 70.0
FF_PANEL_IPHONE_PRICE = 100.0


class SettingsStates(StatesGroup):
    waiting_phone_model = State()
    waiting_confirm = State()
    waiting_payment_method = State()
    waiting_receipt = State()


def _settings_types() -> dict[str, tuple[float, str]]:
    return {
        "ff_settings_basic": (FF_BASIC_PRICE, "🎯 Обычные (40-65%)"),
        "ff_settings_vip": (FF_VIP_SETTINGS_PRICE, "👑 VIP (80-85%)"),
        "ff_panel_android": (FF_PANEL_ANDROID_PRICE, "Панел для Android"),
        "ff_panel_iphone": (FF_PANEL_IPHONE_PRICE, "Панел для iPhone"),
    }


@router.callback_query(F.data == "ff_settings")
async def ff_settings_open(callback: CallbackQuery, t) -> None:
    await callback.answer()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("ff_settings_basic_label", price=fmt_price(FF_BASIC_PRICE)), callback_data="ffs_basic")],
            [InlineKeyboardButton(text=t("ff_settings_vip_label", price=fmt_price(FF_VIP_SETTINGS_PRICE)), callback_data="ffs_vip")],
            [InlineKeyboardButton(text=t("back"), callback_data="ff_choose_category")],
        ]
    )
    await callback.message.answer(t("ff_settings_choose"), reply_markup=kb)


@router.callback_query(F.data == "ff_vip")
async def ff_panel_choose(callback: CallbackQuery, t) -> None:
    await callback.answer()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("ff_panel_android"), callback_data="ff_panel_android")],
            [InlineKeyboardButton(text=t("ff_panel_iphone"), callback_data="ff_panel_iphone")],
            [InlineKeyboardButton(text=t("back"), callback_data="ff_choose_category")],
        ]
    )
    await callback.message.answer(t("ff_panel_choose"), reply_markup=kb)


@router.callback_query(F.data.in_(("ffs_basic", "ffs_vip", "ff_panel_android", "ff_panel_iphone")))
async def ff_settings_selected(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    mapping = {
        "ffs_basic": "ff_settings_basic",
        "ffs_vip": "ff_settings_vip",
        "ff_panel_android": "ff_panel_android",
        "ff_panel_iphone": "ff_panel_iphone",
    }
    order_type = mapping[callback.data]
    price = _settings_types()[order_type][0]
    await state.set_state(SettingsStates.waiting_phone_model)
    await state.update_data(order_type=order_type, price=price)
    await callback.message.answer(t("ff_enter_phone"))


@router.message(StateFilter(SettingsStates.waiting_phone_model), F.text)
async def ff_settings_phone(message: Message, state: FSMContext, t) -> None:
    phone = (message.text or "").strip()
    if len(phone) < 5 or phone.isdigit():
        await message.answer(t("ff_invalid_phone"))
        return
    data = await state.get_data()
    order_type = data["order_type"]
    price = float(data["price"])
    await state.update_data(phone_model=phone)
    await state.set_state(SettingsStates.waiting_confirm)
    if order_type in ("ff_panel_android", "ff_panel_iphone"):
        panel_type = _settings_types()[order_type][1]
        text = t(
            "ff_panel_summary",
            name=message.from_user.full_name,
            username=message.from_user.username or "нет",
            panel_type=panel_type,
            phone=phone,
            price=fmt_price(price),
        )
    else:
        text = t(
            "ff_settings_summary",
            name=message.from_user.full_name,
            username=message.from_user.username or "нет",
            settings_type=_settings_types()[order_type][1],
            phone=phone,
            price=fmt_price(price),
        )
    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=t("confirm_yes"), callback_data="ffs_confirm")],
                [InlineKeyboardButton(text=t("confirm_no"), callback_data="ffs_cancel")],
            ]
        ),
    )


@router.callback_query(F.data == "ffs_cancel", StateFilter("*"))
async def ff_settings_cancel(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    cur = await state.get_state()
    if cur and cur.startswith("SettingsStates:"):
        await state.clear()
        await callback.message.answer(t("order_cancelled"))


@router.callback_query(F.data == "ffs_confirm", StateFilter(SettingsStates.waiting_confirm))
async def ff_settings_go_payment(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    await show_payment_methods(callback.from_user.id, str(data["price"]), "смн")
    await state.set_state(SettingsStates.waiting_payment_method)


@router.callback_query(
    F.data.in_(["pay_dc", "pay_alif"]),
    StateFilter(SettingsStates.waiting_payment_method),
)
async def settings_payment_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    await state.update_data(payment_method=callback.data)
    await show_requisites(callback.from_user.id, callback.data, str(data.get("price")), "смн")
    await state.set_state(SettingsStates.waiting_receipt)
    await callback.message.answer("📸 Отправьте скриншот чека (фото).")


@router.message(StateFilter(SettingsStates.waiting_receipt), F.photo)
async def settings_receipt_received(message: Message, state: FSMContext, bot, t) -> None:
    is_dup, dup_text = await check_receipt(message, "settings", t)
    if is_dup:
        await message.answer(dup_text, parse_mode="HTML")
        return

    data = await state.get_data()
    photo = message.photo[-1]
    photo_id = photo.file_id
    order_type = data.get("order_type")
    db_order_type = order_type
    if order_type == "ff_panel_android":
        db_order_type = "ff_panel_android"
    elif order_type == "ff_panel_iphone":
        db_order_type = "ff_panel_iphone"

    order_id = await db.create_settings_order(
        user_tg_id=message.from_user.id,
        username=message.from_user.username or "",
        order_type=db_order_type,
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

    if order_type in ("ff_panel_android", "ff_panel_iphone"):
        panel_label = "Android" if order_type == "ff_panel_android" else "iPhone"
        admin_text = (
            f"👑 ЗАКАЗ — Панел FF #{order_id}\n"
            "───────────────────────\n"
            f"👤 {message.from_user.full_name} | @{message.from_user.username or 'нет'}\n"
            f"📱 Тип: {panel_label}\n"
            f"📱 Телефон: {data.get('phone_model')}\n"
            f"💰 {fmt_price(float(data.get('price') or 0))} смн | 💳 {data.get('payment_method')}"
        )
    else:
        settings_type = _settings_types().get(str(order_type), (0.0, str(order_type)))[1]
        admin_text = (
            f"⚙️ НОВЫЙ ЗАКАЗ — {settings_type} FF #{order_id}\n"
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
            [{"text": "📤 Отправить файл", "callback_data": f"send_vip_{order_id}", "style": "primary"}],
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


@router.message(StateFilter(SettingsStates.waiting_receipt), ~F.photo)
async def settings_wrong_receipt(message: Message, t) -> None:
    await message.answer(t("receipt_need_photo"))
