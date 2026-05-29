from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from config import config
from database import queries as db
from utils.locale_text import get_locale_string


class BanCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id: int | None = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id and user_id not in config.admin_ids_list:
            if await db.is_user_banned(user_id):
                ban_info = await db.get_banned_user(user_id)
                reason = (ban_info or {}).get("reason") or ""
                t = data.get("t")
                if callable(t):
                    text = t("banned_message", reason=reason)
                    alert = "🚫 Ваш доступ ограничен. Свяжитесь с @vvewrix"
                else:
                    lang = "ru"
                    try:
                        lang = await db.get_user_language(user_id)
                    except Exception:
                        pass
                    if lang not in ("ru", "tj"):
                        lang = "ru"
                    text = get_locale_string(lang, "banned_message", reason=reason)
                    alert = "🚫 @vvewrix"
                if isinstance(event, Message):
                    await event.answer(text, parse_mode="HTML")
                elif isinstance(event, CallbackQuery):
                    await event.answer(alert, show_alert=True)
                return None

        return await handler(event, data)

# ✅ ГОТОВО: middlewares/ban_check.py
