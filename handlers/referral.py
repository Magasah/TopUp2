from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from database.queries import count_referrals

router = Router()


@router.callback_query(F.data == "my_referrals")
async def show_referrals(callback: CallbackQuery, t) -> None:
    await callback.answer()
    uid = callback.from_user.id
    bot_info = await callback.bot.get_me()
    uname = (bot_info.username or "").strip()
    ref_link = f"https://t.me/{uname}?start=ref_{uid}" if uname else ""

    total = await count_referrals(uid)

    text = (
        f"{t('referral_screen')}\n"
        f"───────────────────────────\n\n"
        f"{t('referral_count_line', count=total)}\n\n"
        f"───────────────────────────\n"
        f"{t('referral_link_label')}\n"
        f"<code>{ref_link}</code>"
    )

    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=t("referral_send_link_btn"),
                callback_data="ref_send_my_link",
            )
        ],
        [
            InlineKeyboardButton(
                text=t("back"),
                callback_data="settings",
            )
        ],
    ]
    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data == "ref_send_my_link")
async def ref_send_my_link(callback: CallbackQuery, t) -> None:
    await callback.answer()
    me = await callback.bot.get_me()
    un = (me.username or "").strip()
    if not un:
        await callback.message.answer(t("referral_link_unavailable"))
        return
    link = f"https://t.me/{un}?start=ref_{callback.from_user.id}"
    await callback.message.answer(link)

# ✅ ГОТОВО: handlers/referral.py
