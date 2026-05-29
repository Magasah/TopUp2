"""Админ-раздел «Кошельки»: редактирование номеров Alif Mobi, DC City и др.

Номера хранятся в таблице `settings` (ключи wallet_*). Если в БД пусто —
используется значение из .env как запасной вариант. Витрина оплаты
(utils/payment_flow.py) читает те же ключи.
"""

import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import config
from database.queries import get_setting, set_setting

router = Router()

# key -> (заголовок, ключ настройки в БД, дефолт из .env, нужен ли формат +992)
WALLETS: dict[str, dict] = {
    "alif": {
        "title": "📱 Alif Mobi",
        "setting": "wallet_alif",
        "env": (config.ALIF_NUMBER or "").strip(),
        "phone": True,
    },
    "dc": {
        "title": "🏦 DC City",
        "setting": "wallet_dc",
        "env": (config.DC_CITY_NUMBER or "").strip(),
        "phone": True,
    },
}

_PHONE_RE = re.compile(r"^\+992\d{9}$")


class WalletStates(StatesGroup):
    waiting_number = State()


async def current_wallet_number(key: str) -> str:
    """Актуальный номер кошелька: сперва БД, затем .env."""
    meta = WALLETS.get(key)
    if not meta:
        return ""
    value = await get_setting(meta["setting"])
    return (value or meta["env"] or "").strip()


def _menu_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=meta["title"], callback_data=f"wallet_edit_{key}")]
        for key, meta in WALLETS.items()
    ]
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="adm_back_panel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _menu_text() -> str:
    lines = ["💳 КОШЕЛЬКИ", "─────────────────────", "Текущие реквизиты:", ""]
    for key, meta in WALLETS.items():
        number = await current_wallet_number(key)
        lines.append(f"{meta['title']}: {number or '— не задан —'}")
    lines.append("")
    lines.append("Нажмите кошелёк, чтобы изменить номер.")
    return "\n".join(lines)


@router.callback_query(F.data == "admin_wallets")
async def wallets_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    try:
        await callback.message.edit_text(await _menu_text(), reply_markup=_menu_kb())
    except Exception:
        await callback.message.answer(await _menu_text(), reply_markup=_menu_kb())


@router.callback_query(F.data.startswith("wallet_edit_"))
async def wallet_edit_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    key = (callback.data or "").removeprefix("wallet_edit_")
    meta = WALLETS.get(key)
    if not meta:
        return
    await state.set_state(WalletStates.waiting_number)
    await state.update_data(wallet_key=key)
    hint = "в формате +992XXXXXXXXX" if meta["phone"] else "(номер карты/счёта)"
    cur = await current_wallet_number(key)
    await callback.message.answer(
        f"Введите новый номер для {meta['title']} {hint}.\n"
        f"Текущий: {cur or '— не задан —'}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Отменить", callback_data="admin_wallets")]]
        ),
    )


@router.message(WalletStates.waiting_number, F.text)
async def wallet_edit_finish(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    key = str(data.get("wallet_key") or "")
    meta = WALLETS.get(key)
    if not meta:
        await state.clear()
        return
    raw = (message.text or "").strip()
    if meta["phone"]:
        normalized = raw.replace(" ", "").replace("-", "")
        if not _PHONE_RE.match(normalized):
            await message.answer(
                "❌ Неверный формат. Номер должен быть в виде +992XXXXXXXXX (9 цифр после +992)."
            )
            return
        raw = normalized
    else:
        digits = re.sub(r"\D", "", raw)
        if not (12 <= len(digits) <= 19):
            await message.answer("❌ Неверный номер карты/счёта (ожидается 12–19 цифр).")
            return
        raw = digits
    await set_setting(meta["setting"], raw)
    await state.clear()
    await message.answer(
        f"✅ Номер для {meta['title']} обновлён:\n<code>{raw}</code>",
        parse_mode="HTML",
    )
    await message.answer(await _menu_text(), reply_markup=_menu_kb())


@router.message(WalletStates.waiting_number)
async def wallet_edit_not_text(message: Message) -> None:
    await message.answer("❌ Отправьте номер текстом.")
