"""Админ-раздел «Админы»: просмотр, добавление и удаление администраторов.

Супер-админы (из .env ADMIN_IDS) показаны с 👑 и не удаляются через панель.
Динамические админы хранятся в таблице БД `admins`. После любого изменения
обновляется кэш в utils.admins, чтобы middlewares сразу видели новые права.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database.queries import (
    add_admin,
    get_admins_full,
    get_user_by_id,
    get_user_by_username,
    remove_admin,
)
from utils.admins import (
    get_super_admin_ids,
    is_super_admin,
    refresh_admins_cache,
)

router = Router()


class AdminMgrStates(StatesGroup):
    waiting_new_admin = State()


async def _menu() -> tuple[str, InlineKeyboardMarkup]:
    super_ids = set(get_super_admin_ids())
    db_admins = await get_admins_full()

    lines = ["👮 АДМИНИСТРАТОРЫ", "─────────────────────"]
    lines.append("👑 Супер-админы (из .env, неизменяемые):")
    for sid in sorted(super_ids):
        lines.append(f"  • <code>{sid}</code>")
    lines.append("")
    lines.append("➕ Добавленные через панель:")
    rows: list[list[InlineKeyboardButton]] = []
    dynamic = [a for a in db_admins if int(a["user_id"]) not in super_ids]
    if dynamic:
        for a in dynamic:
            uid = int(a["user_id"])
            uname = f"@{a['username']}" if a.get("username") else str(uid)
            lines.append(f"  • {uname} (<code>{uid}</code>)")
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"🗑 Удалить {uname}",
                        callback_data=f"admin_rm_{uid}",
                    )
                ]
            )
    else:
        lines.append("  — пусто —")

    rows.append([InlineKeyboardButton(text="➕ Добавить админа", callback_data="admin_add_new")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="adm_back_panel")])
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "admin_admins")
async def admins_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    text, kb = await _menu()
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "admin_add_new")
async def admin_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(AdminMgrStates.waiting_new_admin)
    await callback.message.answer(
        "Отправьте ID пользователя (число) или @username нового админа.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Отменить", callback_data="admin_admins")]]
        ),
    )


@router.message(AdminMgrStates.waiting_new_admin, F.text)
async def admin_add_finish(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    new_id: int | None = None
    username: str | None = None

    if raw.lstrip("-").isdigit():
        new_id = int(raw)
        user = await get_user_by_id(new_id)
        username = (user or {}).get("username")
    elif raw.startswith("@"):
        user = await get_user_by_username(raw.lstrip("@"))
        if user:
            new_id = int(user["tg_id"])
            username = user.get("username")
        else:
            await message.answer(
                "❌ Пользователь с таким @username не найден в базе. "
                "Попросите его написать боту /start или укажите числовой ID."
            )
            return
    else:
        await message.answer("❌ Введите числовой ID или @username.")
        return

    if new_id is None:
        await message.answer("❌ Не удалось определить ID пользователя.")
        return

    await add_admin(new_id, username=username, added_by=message.from_user.id)
    await refresh_admins_cache()
    await state.clear()
    await message.answer(f"✅ Админ добавлен: <code>{new_id}</code>", parse_mode="HTML")
    text, kb = await _menu()
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_rm_"))
async def admin_remove(callback: CallbackQuery) -> None:
    await callback.answer()
    uid = int((callback.data or "").removeprefix("admin_rm_"))
    if is_super_admin(uid):
        await callback.answer("👑 Супер-админа нельзя удалить через панель.", show_alert=True)
        return
    await remove_admin(uid)
    await refresh_admins_cache()
    text, kb = await _menu()
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
