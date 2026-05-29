import re

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import config
from database import queries as db
from utils import tg_api
from utils.assets import get_game_photo
from utils.currency import format_payment_tjs_usd, get_rate_info, get_usd_rate, usd_to_tjs
from utils.formatter import fmt_price_tjs
from utils.payment_flow import show_payment_methods, show_requisites
from utils.receipt_checker import append_receipt_note, check_receipt, register_receipt

router = Router()

STEAM_LOGIN_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")


class SteamStates(StatesGroup):
    waiting_amount_usd = State()
    waiting_steam_login = State()
    waiting_confirm = State()
    waiting_payment_method = State()
    waiting_receipt = State()


def _steam_quick_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="5$", callback_data="steam_amount_5"),
                InlineKeyboardButton(text="10$", callback_data="steam_amount_10"),
                InlineKeyboardButton(text="20$", callback_data="steam_amount_20"),
                InlineKeyboardButton(text="25$", callback_data="steam_amount_25"),
            ],
            [
                InlineKeyboardButton(text="50$", callback_data="steam_amount_50"),
                InlineKeyboardButton(text="100$", callback_data="steam_amount_100"),
            ],
            [
                InlineKeyboardButton(text="✍️ Ввести вручную", callback_data="steam_manual"),
                InlineKeyboardButton(text="◀️ Назад", callback_data="cancel_payment"),
            ],
        ]
    )


@router.callback_query(F.data == "steam_start")
async def steam_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    rate_info = await get_rate_info()
    text = (
        "🎮 Steam — пополнение кошелька\n"
        "─────────────────────────────\n"
        "💵 Пополнение в долларах США\n"
        f"{rate_info}\n"
        "─────────────────────────────\n"
        "Введите сумму в USD (например: 5, 10, 25, 50):"
    )
    photo = get_game_photo("steam")
    if photo:
        await callback.bot.send_photo(
            callback.from_user.id,
            photo=photo,
            caption=text,
            parse_mode="HTML",
            reply_markup=_steam_quick_kb(),
        )
    else:
        await callback.message.answer(text, reply_markup=_steam_quick_kb())
    await state.set_state(SteamStates.waiting_amount_usd)


@router.callback_query(StateFilter(SteamStates.waiting_amount_usd), F.data == "steam_manual")
async def steam_manual(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer("✍️ Введите сумму вручную в USD, например: 12.5")


async def _handle_amount_input(message: Message, state: FSMContext, raw_text: str) -> None:
    raw = raw_text.replace("$", "").replace(",", ".").strip()
    try:
        amount_usd = float(raw)
    except ValueError:
        await message.answer("❌ Введите число. Например: 10 или 25.50")
        return
    if amount_usd < 1:
        await message.answer("❌ Минимум $1")
        return
    if amount_usd > 500:
        await message.answer("❌ Максимум $500")
        return
    amount_tjs = await usd_to_tjs(amount_usd)
    rate = await get_usd_rate()
    await state.update_data(amount_usd=amount_usd, amount_tjs=amount_tjs, usd_rate=rate)
    await state.set_state(SteamStates.waiting_steam_login)
    await message.answer(
        "👤 Введите логин Steam\n"
        "─────────────────────────────\n"
        "Логин (не никнейм, а имя аккаунта):\n"
        "Например: mygamer123\n\n"
        "⚠️ Проверьте что логин введён точно!",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="steam_start")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment")],
            ]
        ),
    )


@router.callback_query(StateFilter(SteamStates.waiting_amount_usd), F.data.startswith("steam_amount_"))
async def steam_amount_quick(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    raw = (callback.data or "").removeprefix("steam_amount_")
    try:
        amount_usd = float(raw)
    except ValueError:
        await callback.message.answer("❌ Введите число. Например: 10 или 25.50")
        return
    amount_tjs = await usd_to_tjs(amount_usd)
    rate = await get_usd_rate()
    await state.update_data(amount_usd=amount_usd, amount_tjs=amount_tjs, usd_rate=rate)
    await state.set_state(SteamStates.waiting_steam_login)
    await callback.message.answer(
        "👤 Введите логин Steam\n"
        "─────────────────────────────\n"
        "Логин (не никнейм, а имя аккаунта):\n"
        "Например: mygamer123\n\n"
        "⚠️ Проверьте что логин введён точно!",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="steam_start")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment")],
            ]
        ),
    )


@router.message(StateFilter(SteamStates.waiting_amount_usd), F.text)
async def steam_amount_text(message: Message, state: FSMContext) -> None:
    await _handle_amount_input(message, state, message.text or "")


@router.message(StateFilter(SteamStates.waiting_steam_login), F.text)
async def steam_login(message: Message, state: FSMContext) -> None:
    steam_login = (message.text or "").strip()
    if not STEAM_LOGIN_RE.fullmatch(steam_login):
        await message.answer("❌ Логин 3-32 символа (латиница, цифры, _-.)")
        return
    await state.update_data(steam_login=steam_login)
    data = await state.get_data()
    await state.set_state(SteamStates.waiting_confirm)
    await message.answer(
        "📋 ВАША ЗАЯВКА — Steam\n"
        "─────────────────────────────\n"
        f"👤 Покупатель: {message.from_user.full_name}\n"
        f"📱 Telegram: @{message.from_user.username or 'нет'}\n"
        "🎮 Сервис: Steam\n"
        f"👤 Логин Steam: {steam_login}\n"
        f"💵 Сумма: {float(data['amount_usd']):g} USD\n"
        f"💰 К оплате: {fmt_price_tjs(float(data['amount_tjs']))}\n"
        f"📈 Курс: 1 USD = {float(data['usd_rate']):g} смн\n"
        "─────────────────────────────\n"
        "Всё верно?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Оплатить", callback_data="steam_confirm_pay")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="steam_start")],
                [InlineKeyboardButton(text="❌ Отмена → меню", callback_data="cancel_payment")],
            ]
        ),
    )


@router.callback_query(StateFilter(SteamStates.waiting_confirm), F.data == "steam_confirm_pay")
async def steam_confirm_pay(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    await show_payment_methods(callback.from_user.id, f"{float(data['amount_tjs']):g}", "смн")
    await state.set_state(SteamStates.waiting_payment_method)


@router.callback_query(StateFilter(SteamStates.waiting_receipt), F.data == "steam_confirm_pay")
async def steam_back_to_payment_methods(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    await show_payment_methods(callback.from_user.id, f"{float(data['amount_tjs']):g}", "смн")
    await state.set_state(SteamStates.waiting_payment_method)


@router.callback_query(
    StateFilter(SteamStates.waiting_payment_method),
    F.data.in_(["pay_dc", "pay_alif"]),
)
async def steam_payment_method(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    await state.update_data(payment_method=callback.data)
    await show_requisites(callback.from_user.id, callback.data, f"{float(data['amount_tjs']):g}", "смн")
    await callback.message.answer(
        format_payment_tjs_usd(
            float(data["amount_tjs"]),
            float(data["amount_usd"]),
            float(data["usd_rate"]),
        )
        + "\n\n📸 Отправьте фото чека.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="steam_confirm_pay")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment")],
            ]
        ),
    )
    await state.set_state(SteamStates.waiting_receipt)


@router.message(StateFilter(SteamStates.waiting_receipt), F.photo)
async def steam_receipt(message: Message, state: FSMContext, t) -> None:
    is_dup, dup_text = await check_receipt(message, "steam", t)
    if is_dup:
        await message.answer(dup_text, parse_mode="HTML")
        return

    data = await state.get_data()
    photo = message.photo[-1]
    photo_id = photo.file_id
    order_id = await db.create_steam_order(
        user_tg_id=message.from_user.id,
        username=message.from_user.username or "",
        steam_login=str(data["steam_login"]),
        amount_usd=float(data["amount_usd"]),
        amount_tjs=float(data["amount_tjs"]),
        usd_rate=float(data["usd_rate"]),
        payment_method=str(data["payment_method"]),
        receipt_file_id=photo_id,
    )
    await register_receipt(
        photo.file_unique_id, photo_id, message.from_user.id, "steam", order_id
    )
    await state.clear()
    await message.answer(
        f"✅ Заявка #{order_id} принята!\n"
        "─────────────────────────────\n"
        f"🎮 Steam | @{data['steam_login']}\n"
        f"💵 {float(data['amount_usd']):g} USD ({float(data['amount_tjs']):g} смн)\n"
        "⏳ Ожидайте выполнения (5-30 мин)"
    )
    admin_text = (
        f"🎮 НОВЫЙ ЗАКАЗ Steam #{order_id}\n"
        "─────────────────────────────\n"
        f"👤 {message.from_user.full_name} | @{message.from_user.username or 'нет'}\n"
        f"👤 Steam логин: {data['steam_login']}\n"
        f"💵 Сумма: {float(data['amount_usd']):g} USD\n"
        f"💰 Оплачено: {float(data['amount_tjs']):g} смн\n"
        f"📈 Курс: 1 USD = {float(data['usd_rate']):g} смн\n"
        f"💳 Оплата: {data['payment_method']}"
    )
    admin_text = append_receipt_note(admin_text, t)
    admin_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять", callback_data=f"order_accept_steam_{order_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"order_reject_steam_{order_id}"),
                InlineKeyboardButton(text="💬 Написать", url=f"tg://user?id={message.from_user.id}"),
            ],
            [InlineKeyboardButton(text="🗑 Удалить заказ", callback_data=f"order_delete_steam_{order_id}")],
        ]
    )
    for admin_id in config.admin_ids_list:
        try:
            await message.bot.send_photo(admin_id, photo=photo_id, caption=admin_text, parse_mode="HTML")
            await message.bot.send_message(admin_id, "Управление заказом:", reply_markup=admin_kb)
        except Exception:
            pass


@router.message(StateFilter(SteamStates.waiting_receipt), ~F.photo)
async def steam_wrong_receipt(message: Message) -> None:
    await message.answer("❌ Отправьте именно фото чека.")
