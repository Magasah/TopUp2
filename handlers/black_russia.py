import logging
import re
from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import config
from database import queries as db
from utils.assets import get_game_photo
from utils import tg_api
from utils.receipt_checker import append_receipt_note, check_receipt, register_receipt
from utils.payment_flow import show_payment_methods, show_requisites

router = Router()

BR_SERVERS = [
    "RED", "ORANGE", "YELLOW", "LIME", "GREEN", "CYAN", "BLUE", "VIOLET",
    "PINK", "WHITE", "BLACK", "GOLD", "SILVER", "RUBY", "SAPPHIRE",
    "EMERALD", "TOPAZ", "AMBER", "CRYSTAL", "DIAMOND",
    "SERVER1", "SERVER2", "SERVER3", "SERVER4", "SERVER5", "SERVER6",
    "SERVER7", "SERVER8", "SERVER9", "SERVER10", "SERVER11", "SERVER12",
    "SERVER13", "SERVER14", "SERVER15", "SERVER16", "SERVER17", "SERVER18",
    "SERVER19", "SERVER20", "SERVER21", "SERVER22", "SERVER23", "SERVER24",
    "SERVER25", "SERVER26", "SERVER27", "SERVER28", "SERVER29", "SERVER30",
    "SERVER31", "SERVER32", "SERVER33", "SERVER34", "SERVER35", "SERVER36",
    "SERVER37", "SERVER38", "SERVER39", "SERVER40", "SERVER41", "SERVER42",
    "SERVER43", "SERVER44", "SERVER45", "SERVER46", "SERVER47", "SERVER48",
    "SERVER49", "SERVER50", "SERVER51", "SERVER52", "SERVER53", "SERVER54",
    "SERVER55", "SERVER56", "SERVER57", "SERVER58", "SERVER59", "SERVER60",
    "SERVER61", "SERVER62", "SERVER63", "SERVER64", "SERVER65", "SERVER66",
    "SERVER67", "SERVER68", "SERVER69", "SERVER70", "SERVER71",
]
BR_SERVER_RE = re.compile(r"^[A-Z0-9]{2,20}$")
BR_NICK_RE = re.compile(r"^[A-Za-z0-9_ ]{3,24}$")


class BRStates(StatesGroup):
    waiting_server = State()
    confirm_server = State()
    waiting_amount = State()
    waiting_nickname = State()
    waiting_confirm = State()
    waiting_pay_method = State()
    waiting_receipt = State()


def _fmt_rub(amount: float) -> str:
    return f"{int(amount)} ₽" if float(amount).is_integer() else f"{amount:g} ₽"


def _quick_servers_kb() -> InlineKeyboardMarkup:
    head = BR_SERVERS[:20]
    rows: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(head), 4):
        rows.append([InlineKeyboardButton(text=s, callback_data=f"br_srv_{s}") for s in head[i:i + 4]])
    rows.append([InlineKeyboardButton(text="✍️ Ввести вручную", callback_data="br_manual_input")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="br_start")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _confirm_unknown_server_kb() -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Всё верно", "callback_data": "br_server_ok", "style": "success"},
                {"text": "✏️ Изменить", "callback_data": "br_server_edit", "style": "primary"},
            ]
        ]
    }


def _confirm_order_kb() -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [{"text": "✅ Оплатить", "callback_data": "br_confirm_pay", "style": "success"}],
            [{"text": "❌ Отмена", "callback_data": "br_cancel_to_menu", "style": "danger"}],
        ]
    }


@router.callback_query(F.data == "br_start")
async def br_welcome(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        text = (
            "🚗 Black Russia\n"
            "───────────────────────\n"
            "💰 Пополнение игрового счёта в рублях\n\n"
            "Выберите действие:"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "💳 Пополнить счёт", "callback_data": "br_topup", "style": "success"}],
                [{"text": "◀️ Назад", "callback_data": "main_menu"}],
            ]
        }
        photo = get_game_photo("black_russia")
        if photo:
            await callback.bot.send_photo(
                callback.from_user.id,
                photo=photo,
                caption=text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="💳 Пополнить счёт", callback_data="br_topup")],
                        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")],
                    ]
                ),
            )
        else:
            await tg_api.send_message(callback.from_user.id, text, kb)
        if callback.message:
            try:
                await callback.message.delete()
            except Exception:
                pass
    except Exception as e:
        logging.exception(f"br_start error: {e}")
        await callback.answer("Ошибка. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data == "br_topup")
async def br_topup(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BRStates.waiting_server)
    text = (
        "🖥 Введите название вашего сервера\n"
        "───────────────────────\n"
        "Например: RED, BLUE, GOLD, SERVER1"
    )
    await callback.message.answer(text, reply_markup=_quick_servers_kb())


@router.callback_query(BRStates.waiting_server, F.data == "br_manual_input")
async def br_manual_input(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer("✍️ Введите сервер вручную:")


@router.callback_query(BRStates.waiting_server, F.data.startswith("br_srv_"))
async def br_server_pick(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    server = (callback.data or "").removeprefix("br_srv_").upper()
    await state.update_data(server=server)
    await state.set_state(BRStates.waiting_amount)
    await callback.message.answer(
        "💰 Введите сумму пополнения\n"
        "───────────────────────\n"
        "Валюта: Российские рубли (₽)\n"
        "Минимум: 50 ₽\n\n"
        "Вы переведёте эту же сумму на карту.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="br_topup")]]
        ),
    )


@router.message(StateFilter(BRStates.waiting_server), F.text)
async def br_server_text(message: Message, state: FSMContext) -> None:
    server = (message.text or "").strip().upper()
    if not BR_SERVER_RE.fullmatch(server):
        await message.answer("❌ Сервер должен быть 2-20 символов: латиница и цифры.")
        return
    await state.update_data(server=server)
    if server not in BR_SERVERS:
        await state.set_state(BRStates.confirm_server)
        await tg_api.send_message(
            message.from_user.id,
            f"⚠️ Сервер '{server}' нет в стандартном списке.\nВсё верно?",
            _confirm_unknown_server_kb(),
        )
        return
    await state.set_state(BRStates.waiting_amount)
    await message.answer(
        "💰 Введите сумму пополнения\n"
        "───────────────────────\n"
        "Валюта: Российские рубли (₽)\n"
        "Минимум: 50 ₽\n\n"
        "Вы переведёте эту же сумму на карту."
    )


@router.callback_query(BRStates.confirm_server, F.data == "br_server_edit")
async def br_server_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BRStates.waiting_server)
    await callback.message.answer("✍️ Введите корректный сервер:")


@router.callback_query(BRStates.confirm_server, F.data == "br_server_ok")
async def br_server_ok(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BRStates.waiting_amount)
    await callback.message.answer(
        "💰 Введите сумму пополнения\n"
        "───────────────────────\n"
        "Валюта: Российские рубли (₽)\n"
        "Минимум: 50 ₽\n\n"
        "Вы переведёте эту же сумму на карту."
    )


@router.message(StateFilter(BRStates.waiting_amount), F.text)
async def br_amount(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().replace(",", ".")
    try:
        amount = float(raw)
    except ValueError:
        await message.answer("❌ Введите число. Например: 100 или 250.5")
        return
    if amount < 50:
        await message.answer("❌ Минимальная сумма: 50 ₽")
        return
    await state.update_data(amount_rub=amount)
    await state.set_state(BRStates.waiting_nickname)
    await message.answer(
        "👾 Введите ваш ник в Black Russia\n"
        "───────────────────────\n"
        "⚠️ Введите точно как в игре!\n"
        "Проверьте заглавные буквы.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="br_back_amount")]]
        ),
    )


@router.callback_query(BRStates.waiting_nickname, F.data == "br_back_amount")
async def br_back_amount(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BRStates.waiting_amount)
    await callback.message.answer("💰 Введите сумму в рублях (минимум 50 ₽):")


@router.message(StateFilter(BRStates.waiting_nickname), F.text)
async def br_nickname(message: Message, state: FSMContext) -> None:
    nickname = (message.text or "").strip()
    if not BR_NICK_RE.fullmatch(nickname):
        await message.answer("❌ Ник должен быть 3-24 символа: латиница, цифры, _, пробел.")
        return
    await state.update_data(nickname=nickname)
    data = await state.get_data()
    await state.set_state(BRStates.waiting_confirm)
    await tg_api.send_message(
        message.from_user.id,
        (
            "📋 ВАША ЗАЯВКА\n"
            "───────────────────────\n"
            f"👤 Покупатель: {message.from_user.full_name}\n"
            f"📱 Telegram: @{message.from_user.username or 'нет'}\n"
            "🚗 Игра: Black Russia\n"
            f"🖥 Сервер: {data['server']}\n"
            f"👾 Ник: {nickname}\n"
            f"💰 Сумма: {_fmt_rub(float(data['amount_rub']))}\n"
            "───────────────────────\n"
            "Всё верно?"
        ),
        _confirm_order_kb(),
    )


@router.callback_query(BRStates.waiting_confirm, F.data == "br_cancel_to_menu")
async def br_cancel_to_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.answer("❌ Заявка отменена.")


@router.callback_query(BRStates.waiting_confirm, F.data == "br_confirm_pay")
async def br_confirm_pay(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    await show_payment_methods(callback.from_user.id, f"{float(data['amount_rub']):g}", "₽")
    await state.set_state(BRStates.waiting_pay_method)


@router.callback_query(
    StateFilter(BRStates.waiting_pay_method),
    F.data.in_(["pay_dc", "pay_alif"]),
)
async def br_pay_method(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    await state.update_data(payment_method=callback.data)
    await show_requisites(
        callback.from_user.id,
        callback.data,
        f"{float(data['amount_rub']):g}",
        "₽",
    )
    await state.set_state(BRStates.waiting_receipt)
    await callback.message.answer(
        "📸 Отправьте скриншот чека (фото). Если передумали, нажмите «Отменить оплату»."
    )
    if callback.message:
        try:
            await callback.message.delete()
        except Exception:
            pass


@router.message(StateFilter(BRStates.waiting_receipt), F.photo)
async def br_receipt(message: Message, state: FSMContext, bot, t) -> None:
    is_dup, dup_text = await check_receipt(message, "br", t)
    if is_dup:
        await message.answer(dup_text, parse_mode="HTML")
        return

    data = await state.get_data()
    photo = message.photo[-1]
    photo_id = photo.file_id
    order_id = await db.create_br_order(
        user_tg_id=message.from_user.id,
        username=message.from_user.username or "",
        server_name=data["server"],
        nickname=data["nickname"],
        amount=float(data["amount_rub"]),
        payment_method=data["payment_method"],
        receipt_file_id=photo_id,
    )
    await register_receipt(
        photo.file_unique_id, photo_id, message.from_user.id, "br", order_id
    )
    await state.clear()
    await message.answer(t("br_order_created", oid=order_id))
    admin_text = (
        f"🚗 НОВЫЙ ЗАКАЗ Black Russia #{order_id}\n"
        "───────────────────────\n"
        f"👤 {message.from_user.full_name}\n"
        f"📱 @{message.from_user.username or 'нет'} | {message.from_user.id}\n"
        f"🖥 Сервер: {data['server']}\n"
        f"👾 Ник: {data['nickname']}\n"
        f"💰 Сумма: {_fmt_rub(float(data['amount_rub']))}\n"
        f"💳 Оплата: {data['payment_method']}"
    )
    admin_text = append_receipt_note(admin_text, t)
    admin_kb = {
        "inline_keyboard": [
            [
                {"text": "✅ Принять", "callback_data": f"br_accept_{order_id}", "style": "success"},
                {"text": "❌ Отклонить", "callback_data": f"br_reject_{order_id}", "style": "danger"},
            ],
            [{"text": "💬 Написать покупателю", "url": f"tg://user?id={message.from_user.id}"}],
            [{"text": "🗑 Удалить заказ", "callback_data": f"br_delete_{order_id}", "style": "danger"}],
        ]
    }
    for admin_id in config.admin_ids_list:
        try:
            await bot.send_photo(admin_id, photo_id, caption=admin_text, parse_mode="HTML")
            await tg_api.send_message(admin_id, "Управление заказом:", admin_kb)
        except Exception:
            pass


@router.message(StateFilter(BRStates.waiting_receipt), ~F.photo)
async def br_wrong_receipt(message: Message, t) -> None:
    await message.answer(t("receipt_need_photo"))

# ✅ ГОТОВО: handlers/black_russia.py
