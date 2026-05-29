from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

router = Router()


def admin_main_kb(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Заказы", callback_data="admin_orders"),
                InlineKeyboardButton(text="📦 Товары", callback_data="admin_products"),
            ],
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats"),
                InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast_start"),
            ],
            [
                InlineKeyboardButton(text="💳 Кошельки", callback_data="admin_wallets"),
                InlineKeyboardButton(text="👮 Админы", callback_data="admin_admins"),
            ],
            [
                InlineKeyboardButton(text="🔧 Разработка", callback_data="admin_maintenance"),
            ],
            [
                InlineKeyboardButton(text=t("req_sub_button"), callback_data="admin_required_subs"),
            ],
        ]
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message, t) -> None:
    await message.answer(
        t("admin_panel"),
        reply_markup=admin_main_kb(t),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data.in_(("adm_back_panel", "admin_panel")))
async def adm_back_panel(callback: CallbackQuery, t) -> None:
    await callback.answer()
    try:
        await callback.message.edit_text(
            t("admin_panel"),
            reply_markup=admin_main_kb(t),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        await callback.message.answer(
            t("admin_panel"),
            reply_markup=admin_main_kb(t),
            parse_mode=ParseMode.HTML,
        )


# ✅ ГОТОВО: handlers/admin/panel.py
