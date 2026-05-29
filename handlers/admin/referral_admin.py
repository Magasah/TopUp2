from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from config import config
from database.queries import (
    count_buying_referrals,
    count_referrals,
    get_pending_rewards,
    update_reward_status,
)

router = Router()


@router.callback_query(F.data == "admin_referrals")
async def admin_referrals(callback: CallbackQuery, t) -> None:
    await callback.answer()
    rewards = await get_pending_rewards()
    if not rewards:
        await callback.message.answer(t("referral_admin_empty"))
        return
    rows: list[list[InlineKeyboardButton]] = []
    for r in rewards:
        uid = int(r["user_id"])
        try:
            chat = await callback.bot.get_chat(uid)
            label = f"@{chat.username}" if chat.username else str(uid)
        except Exception:
            label = str(uid)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"⏳ {label}",
                    callback_data=f"ref_view_{uid}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=t("back"),
                callback_data="adm_back_panel",
            )
        ]
    )
    await callback.message.answer(
        t("referral_admin_title_list"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("ref_view_"))
async def ref_view(callback: CallbackQuery, t) -> None:
    await callback.answer()
    uid = int((callback.data or "").removeprefix("ref_view_"))

    total = await count_referrals(uid)
    buyers = await count_buying_referrals(uid)
    try:
        chat = await callback.bot.get_chat(uid)
        cap = (
            f"🎁 <b>{t('referral_admin_candidate')}</b>\n"
            f"👤 {chat.full_name} | @{chat.username or '—'}\n"
            f"🆔 <code>{uid}</code>\n"
            f"👥 {t('referral_invited_progress', current=total)}\n"
            f"💰 {t('referral_buyers_progress', current=buyers)}"
        )
    except Exception:
        cap = t("referral_admin_user_unavailable", uid=uid)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("accept"),
                    callback_data=f"ref_approve_{uid}",
                ),
                InlineKeyboardButton(
                    text=t("reject"),
                    callback_data=f"ref_reject_{uid}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("write_buyer"),
                    url=f"tg://user?id={uid}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("back"),
                    callback_data="admin_referrals",
                )
            ],
        ]
    )
    await callback.message.answer(cap, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("ref_approve_"))
async def approve_reward(callback: CallbackQuery, t) -> None:
    await callback.answer()
    uid = int((callback.data or "").removeprefix("ref_approve_"))
    await update_reward_status(uid, "approved")
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(t("referral_reward_approved_admin"))
    admin_mention = (config.ADMIN_TG or "").lstrip("@")
    user_msg = t("referral_reward_approved_user", admin=admin_mention)
    try:
        await callback.bot.send_message(uid, user_msg, parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data.startswith("ref_reject_"))
async def reject_reward(callback: CallbackQuery, t) -> None:
    await callback.answer()
    uid = int((callback.data or "").removeprefix("ref_reject_"))
    await update_reward_status(uid, "rejected")
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(t("referral_reward_rejected_admin"))
    try:
        await callback.bot.send_message(uid, t("referral_reward_rejected_user"))
    except Exception:
        pass

# ✅ ГОТОВО: handlers/admin/referral_admin.py
