from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from urllib.parse import quote

from config import config
from handlers.gifts_webapp import append_gifts_menu_row
from database import queries as db
from utils.assets import get_game_photo
from utils.currency import format_payment_tjs_usd, get_rate_info, usd_to_tjs_with_markup
from utils.formatter import fmt_price_tjs
from utils.payment_flow import show_payment_methods, show_requisites
from utils.receipt_checker import append_receipt_note, check_receipt, register_receipt

router = Router()

STARS_PACKS = {
    "100": 2.00,
    "150": 2.99,
    "250": 5.03,
    "350": 7.08,
    "500": 10.07,
    "750": 15.24,
    "1000": 20.42,
    "1500": 32.67,
    "2500": 51.73,
    "5000": 100.73,
    "10000": 201.47,
}

PREMIUM_PACKS = {"1m": 4.5, "3m": 15.0, "6m": 21.0, "12m": 37.0}
PREMIUM_LABELS = {"1m": "1 месяц", "3m": "3 месяца", "6m": "6 месяцев", "12m": "12 месяцев"}


class TgServiceStates(StatesGroup):
    waiting_target = State()
    waiting_confirm = State()
    waiting_payment_method = State()
    waiting_receipt = State()


@router.callback_query(F.data == "other_menu")
async def other_menu(callback: CallbackQuery, t) -> None:
    await callback.answer()
    rows = [
        [InlineKeyboardButton(text="✈️ Telegram", callback_data="tg_menu")],
        [InlineKeyboardButton(text=t("tg_bot_order_btn"), callback_data="tg_bot_order")],
        [InlineKeyboardButton(text="🤖 ИИ Подписки", callback_data="ai_subs_start")],
    ]
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
    await callback.message.answer(
        f"{t('other_menu_btn')}\n────────────────────\n{t('choose_action')}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data == "tg_menu")
async def tg_menu(callback: CallbackQuery, t) -> None:
    await callback.answer()
    photo = get_game_photo("telegram")
    text = f"{t('telegram_menu_title')}\n────────────────────\n{t('choose_action')}"
    rows = [
        [InlineKeyboardButton(text="⭐ Stars (Звёзды Telegram)", callback_data="tg_stars_menu")],
        [InlineKeyboardButton(text="💎 Telegram Premium", callback_data="tg_premium_menu")],
    ]
    append_gifts_menu_row(rows)
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="other_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    if photo:
        await callback.bot.send_photo(callback.from_user.id, photo=photo, caption=text, parse_mode="HTML", reply_markup=kb)
    else:
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "tg_stars_menu")
async def tg_stars_menu(callback: CallbackQuery, t) -> None:
    await callback.answer()
    rate_info = await get_rate_info()
    rows = [
        [InlineKeyboardButton(text=f"{k} ⭐ — {v:.2f}$", callback_data=f"tg_stars_{k}")]
        for k, v in STARS_PACKS.items()
    ]
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="tg_menu")])
    photo = get_game_photo("telegram_stars")
    text = (
        f"{t('telegram_stars_title')}\n────────────────────\n"
        f"{rate_info}\n"
        f"{t('tg_stars_terms')}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    if photo:
        await callback.bot.send_photo(callback.from_user.id, photo=photo, caption=text, parse_mode="HTML", reply_markup=kb)
    else:
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "tg_premium_menu")
async def tg_premium_menu(callback: CallbackQuery, t) -> None:
    await callback.answer()
    rate_info = await get_rate_info()
    rows = [
        [InlineKeyboardButton(text=f"{PREMIUM_LABELS[key]} — {usd:.2f}$", callback_data=f"tg_premium_{key}")]
        for key, usd in PREMIUM_PACKS.items()
    ]
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="tg_menu")])
    photo = get_game_photo("telegram_premium")
    text = f"{t('telegram_premium_title')}\n────────────────────\n{rate_info}"
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    if photo:
        await callback.bot.send_photo(callback.from_user.id, photo=photo, caption=text, parse_mode="HTML", reply_markup=kb)
    else:
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("tg_stars_"))
async def tg_stars_pick(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    count = callback.data.removeprefix("tg_stars_")
    usd = STARS_PACKS.get(count)
    if usd is None:
        return
    amount_tjs, eff_rate = await usd_to_tjs_with_markup(usd, markup_percent=10.0)
    await state.set_state(TgServiceStates.waiting_target)
    await state.update_data(
        service_type="telegram_stars",
        service_label=f"Telegram Stars {count}",
        amount_usd=usd,
        amount_tjs=amount_tjs,
        usd_rate=eff_rate,
    )
    await callback.message.answer(
        "Введите username/id получателя в Telegram:\n"
        "Пример: @username или 123456789",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="tg_stars_menu")]]
        ),
    )


@router.callback_query(F.data.startswith("tg_premium_"))
async def tg_premium_pick(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    key = callback.data.removeprefix("tg_premium_")
    usd = PREMIUM_PACKS.get(key)
    if usd is None:
        return
    amount_tjs, eff_rate = await usd_to_tjs_with_markup(usd, markup_percent=10.0)
    await state.set_state(TgServiceStates.waiting_target)
    await state.update_data(
        service_type="telegram_premium",
        service_label=f"Telegram Premium {PREMIUM_LABELS[key]}",
        amount_usd=usd,
        amount_tjs=amount_tjs,
        usd_rate=eff_rate,
    )
    await callback.message.answer(
        "Введите username/id Telegram, для кого активировать Premium:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="tg_premium_menu")]]
        ),
    )


@router.message(StateFilter(TgServiceStates.waiting_target), F.text)
async def tg_target(message: Message, state: FSMContext) -> None:
    target = (message.text or "").strip()
    if len(target) < 3:
        await message.answer("❌ Слишком короткий username/id.")
        return
    await state.update_data(target=target)
    data = await state.get_data()
    await state.set_state(TgServiceStates.waiting_confirm)
    await message.answer(
        "📋 ЗАЯВКА Telegram\n────────────────────\n"
        f"👤 Покупатель: {message.from_user.full_name}\n"
        f"📱 Telegram: @{message.from_user.username or 'нет'}\n"
        f"🧾 Услуга: {data['service_label']}\n"
        f"🎯 Получатель: {target}\n"
        f"💵 Сумма: {float(data['amount_usd']):.2f} USD\n"
        f"💰 К оплате: {float(data['amount_tjs']):g} смн\n"
        f"📈 Курс (c наценкой): {float(data['usd_rate']):g}\n"
        "────────────────────\nВсё верно?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Оплатить", callback_data="tg_service_confirm")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment")],
            ]
        ),
    )


@router.callback_query(StateFilter(TgServiceStates.waiting_confirm), F.data == "tg_service_confirm")
async def tg_service_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    await show_payment_methods(callback.from_user.id, f"{float(data['amount_tjs']):g}", "смн")
    await state.set_state(TgServiceStates.waiting_payment_method)


@router.callback_query(
    StateFilter(TgServiceStates.waiting_payment_method),
    F.data.in_(["pay_dc", "pay_alif"]),
)
async def tg_service_payment(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    await state.update_data(payment_method=callback.data)
    await show_requisites(callback.from_user.id, callback.data, f"{float(data['amount_tjs']):g}", "смн")
    await state.set_state(TgServiceStates.waiting_receipt)
    pay_note = format_payment_tjs_usd(
        float(data["amount_tjs"]),
        float(data["amount_usd"]),
        float(data["usd_rate"]),
    )
    await callback.message.answer(
        pay_note + "\n\n📸 Отправьте фото чека.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment")]]
        ),
    )


@router.message(StateFilter(TgServiceStates.waiting_receipt), F.photo)
async def tg_service_receipt(message: Message, state: FSMContext, t) -> None:
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
        order_type=str(data["service_type"]),
        phone_model=str(data["target"]),
        price_tjs=float(data["amount_tjs"]),
        payment_method=str(data["payment_method"]),
        receipt_file_id=photo_id,
    )
    await register_receipt(
        photo.file_unique_id, photo_id, message.from_user.id, "settings", order_id
    )
    await state.clear()
    await message.answer(
        f"✅ Заявка #{order_id} принята!\n"
        f"🧾 {data['service_label']}\n"
        f"🎯 {data['target']}\n"
        f"💰 {fmt_price_tjs(float(data['amount_tjs']))}"
    )
    admin_text = (
        f"✈️ НОВЫЙ ЗАКАЗ Telegram #{order_id}\n"
        "────────────────────\n"
        f"👤 {message.from_user.full_name} | @{message.from_user.username or 'нет'}\n"
        f"🧾 {data['service_label']}\n"
        f"🎯 Получатель: {data['target']}\n"
        f"💵 {float(data['amount_usd']):.2f} USD\n"
        f"💰 {float(data['amount_tjs']):g} смн\n"
        f"📈 Курс: {float(data['usd_rate']):g}\n"
        f"💳 Оплата: {data['payment_method']}"
    )
    admin_text = append_receipt_note(admin_text, t)
    admin_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять", callback_data=f"sord_accept_{order_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"sord_reject_{order_id}"),
            ],
            [InlineKeyboardButton(text="💬 Написать", url=f"tg://user?id={message.from_user.id}")],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"sord_del_{order_id}")],
        ]
    )
    for admin_id in config.admin_ids_list:
        try:
            await message.bot.send_photo(admin_id, photo=photo_id, caption=admin_text, parse_mode="HTML")
            await message.bot.send_message(admin_id, "Управление заказом:", reply_markup=admin_kb)
        except Exception:
            pass


@router.message(StateFilter(TgServiceStates.waiting_receipt), ~F.photo)
async def tg_service_not_photo(message: Message) -> None:
    await message.answer("❌ Нужна фотография чека.")


@router.callback_query(F.data == "tg_bot_order")
async def tg_bot_order(callback: CallbackQuery, t) -> None:
    await callback.answer()
    start_text = "Здравствуйте, я хочу заказать телеграм бота"
    # Жестко фиксируем контакт для заказов разработки бота
    link = f"https://t.me/vvewrix?text={quote(start_text)}"
    fallback_link = "tg://user?id=7734811816"
    photo = get_game_photo("telegram_bot_order")
    text = t("tg_bot_order_text")
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("tg_bot_order_write_btn"), url=link)],
            [InlineKeyboardButton(text="🆔 Написать по ID", url=fallback_link)],
            [InlineKeyboardButton(text=t("back"), callback_data="other_menu")],
        ]
    )
    if photo:
        await callback.bot.send_photo(callback.from_user.id, photo=photo, caption=text, parse_mode="HTML", reply_markup=kb)
    else:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
