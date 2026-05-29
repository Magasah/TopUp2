import os

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import config
from database.queries import set_user_language, upsert_user
from utils.assets import get_game_photo

router = Router()


def _settings_keyboard(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🇷🇺 Русский",
                    callback_data="lang_ru",
                ),
                InlineKeyboardButton(
                    text="🇹🇯 Тоҷикӣ",
                    callback_data="lang_tj",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("referral_program_btn"),
                    callback_data="my_referrals",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("safety_rules_btn"),
                    callback_data="safety_rules",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("back"),
                    callback_data="main_menu",
                )
            ],
        ]
    )


async def _settings_caption(t, tg_id: int) -> str:
    return (
        f"<b>{t('settings_title')}</b>\n\n"
        f"{t('settings_choose_lang')}\n\n"
        f"{t('settings_referral_hint')}"
    )


async def _send_settings_screen(bot, chat_id: int, t, tg_id: int) -> None:
    cap = await _settings_caption(t, tg_id)
    kb = _settings_keyboard(t)
    photo_obj = get_game_photo("welcome")
    photo_path = config.store_photo or ""
    try:
        if photo_obj:
            await bot.send_photo(
                chat_id,
                photo=photo_obj,
                caption=cap,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
        elif photo_path and os.path.isfile(photo_path):
            await bot.send_photo(
                chat_id,
                photo=FSInputFile(photo_path),
                caption=cap,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
        else:
            await bot.send_message(
                chat_id,
                cap,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
    except Exception:
        await bot.send_message(
            chat_id,
            cap,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )


@router.callback_query(F.data == "settings")
async def open_settings_cb(callback: CallbackQuery, t) -> None:
    await callback.answer()
    chat_id = callback.message.chat.id
    await _send_settings_screen(callback.bot, chat_id, t, callback.from_user.id)
    try:
        await callback.message.delete()
    except Exception:
        pass


@router.message(Command("settings"))
async def open_settings_cmd(message: Message, t) -> None:
    await _send_settings_screen(message.bot, message.chat.id, t, message.from_user.id)


@router.callback_query(F.data.in_(("lang_ru", "lang_tj")))
async def set_language(callback: CallbackQuery, t) -> None:
    lang = callback.data.split("_", 1)[1]
    await set_user_language(callback.from_user.id, lang)
    await upsert_user(callback.from_user, language=lang)
    await callback.answer(t("language_saved"), show_alert=True)


@router.callback_query(F.data == "safety_rules")
async def safety_rules(callback: CallbackQuery, t) -> None:
    await callback.answer()
    await callback.message.answer(
        t("safety_rules_text"),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=t("back"), callback_data="settings")]]
        ),
    )

# ✅ ГОТОВО: handlers/settings.py
