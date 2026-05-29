from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from config import config
from database.queries import get_setting, set_setting

router = Router()


def _maintenance_kb(t, enabled: bool) -> InlineKeyboardMarkup:
    if enabled:
        row = [
            InlineKeyboardButton(
                text=t("maintenance_toggle_off"),
                callback_data="maintenance_toggle",
            ),
        ]
    else:
        row = [
            InlineKeyboardButton(
                text=t("maintenance_toggle_on"),
                callback_data="maintenance_toggle",
            ),
        ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            row,
            [InlineKeyboardButton(text=t("back"), callback_data="adm_back_panel")],
        ]
    )


@router.callback_query(F.data == "admin_maintenance")
async def admin_maintenance(callback: CallbackQuery, t) -> None:
    await callback.answer()
    on = (await get_setting("maintenance_mode") or "0").strip() == "1"
    status = (
        "🔧 <b>Режим разработки</b>\n"
        "────────────────────\n"
        + ("🟥 <b>ВКЛ</b> — пользователи видят заглушку." if on else "🟩 <b>ВЫКЛ</b> — обычная работа.")
    )
    await callback.message.answer(
        status,
        parse_mode="HTML",
        reply_markup=_maintenance_kb(t, on),
    )


@router.callback_query(F.data == "maintenance_toggle")
async def maintenance_toggle(callback: CallbackQuery, t) -> None:
    await callback.answer()
    cur = (await get_setting("maintenance_mode") or "0").strip()
    new_val = "0" if cur == "1" else "1"
    await set_setting("maintenance_mode", new_val)
    on = new_val == "1"
    note = t("maintenance_toggle_on") if on else t("maintenance_toggle_off")
    for aid in config.admin_ids_list:
        if aid == callback.from_user.id:
            continue
        try:
            await callback.bot.send_message(
                aid,
                f"🔧 Режим обслуживания: <b>{'ВКЛ' if on else 'ВЫКЛ'}</b>\n{note}",
                parse_mode="HTML",
            )
        except Exception:
            pass
    await callback.message.answer(
        f"✅ {note}",
        reply_markup=_maintenance_kb(t, on),
    )

# ✅ ГОТОВО: handlers/admin/maintenance.py
