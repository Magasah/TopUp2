from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import config
from database.queries import (
    add_referral,
    count_referrals,
    get_all_games,
    get_referral,
    get_user_language,
    record_bot_start_command,
    set_user_language,
    upsert_user,
    user_exists,
)
from keyboards.inline import main_menu_kb
from utils.locale_text import get_locale_string
from utils.tg_api import send_message, send_photo

router = Router()


def _make_t(lang: str):
    def t(key: str, **kwargs) -> str:
        return get_locale_string(lang, key, **kwargs)

    return t


def _first_lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇹🇯 Тоҷикӣ", callback_data="setlang_first_tj"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang_first_ru"),
            ]
        ]
    )


async def _send_main_menu(chat_id: int, first_name: str, t) -> None:
    games = await get_all_games()
    await send_photo(
        chat_id,
        config.welcome_photo,
        t("welcome", name=first_name or ""),
        main_menu_kb(games, t),
    )


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state, t) -> None:
    await state.clear()
    is_new_user = not await user_exists(message.from_user.id)
    await upsert_user(message.from_user)
    await record_bot_start_command()
    args = (command.args or "").strip()
    if args.startswith("ref_"):
        try:
            referrer_id = int(args.split("_", 1)[1])
        except (ValueError, IndexError):
            referrer_id = 0
        if referrer_id and referrer_id != message.from_user.id:
            existing = await get_referral(message.from_user.id)
            if not existing:
                await add_referral(referrer_id, message.from_user.id)
                total = await count_referrals(referrer_id)
                lang = await get_user_language(referrer_id)
                txt = get_locale_string(
                    lang,
                    "referral_notify_new",
                    count=total,
                )
                try:
                    await message.bot.send_message(referrer_id, txt)
                except Exception:
                    pass

    if is_new_user:
        await message.answer(
            "Выберите язык / Забонро интихоб кунед:",
            reply_markup=_first_lang_kb(),
        )
        return

    await _send_main_menu(
        message.chat.id, message.from_user.first_name or "", t
    )


@router.callback_query(F.data.in_(("setlang_first_ru", "setlang_first_tj")))
async def first_lang_chosen(callback: CallbackQuery) -> None:
    await callback.answer()
    lang = callback.data.rsplit("_", 1)[1]
    await set_user_language(callback.from_user.id, lang)
    await upsert_user(callback.from_user, language=lang)
    t = _make_t(lang)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await _send_main_menu(
        callback.message.chat.id, callback.from_user.first_name or "", t
    )


@router.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery, t) -> None:
    await callback.answer()
    chat_id = callback.message.chat.id
    try:
        await callback.message.delete()
    except Exception:
        pass
    games = await get_all_games()
    await send_photo(
        chat_id,
        config.welcome_photo,
        t("welcome", name=callback.from_user.first_name or ""),
        main_menu_kb(games, t),
    )


@router.callback_query(F.data == "support")
async def support_handler(callback: CallbackQuery, t) -> None:
    await callback.answer()
    admin = "@vvewrix"
    kb = {
        "inline_keyboard": [
            [
                {
                    "text": t("support_write"),
                    "url": "https://t.me/vvewrix",
                    "style": "primary",
                }
            ],
            [{"text": t("back"), "callback_data": "main_menu", "style": "primary"}],
        ]
    }
    await send_message(
        callback.message.chat.id,
        f"<b>{t('support_title')}</b>\n\n"
        + t("support_text", admin=admin),
        kb,
    )


@router.callback_query(F.data.in_(("check_subscription", "check_sub")))
async def check_subscription(callback: CallbackQuery, t) -> None:
    try:
        member = await callback.bot.get_chat_member(
            config.channel_id_member_check,
            callback.from_user.id,
        )
        if member.status in ("left", "kicked"):
            await callback.answer(t("not_subscribed"), show_alert=True)
            return
    except Exception:
        await callback.answer(t("not_subscribed"), show_alert=True)
        return
    await callback.answer(t("subscription_confirmed_short"))
    chat_id = callback.message.chat.id
    try:
        await callback.message.delete()
    except Exception:
        pass
    games = await get_all_games()
    await send_photo(
        chat_id,
        config.welcome_photo,
        t("welcome", name=callback.from_user.first_name or ""),
        main_menu_kb(games, t),
    )

# ✅ ГОТОВО: handlers/start.py
