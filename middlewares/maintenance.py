from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from utils.locale_text import get_locale_string


class MaintenanceMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        from config import config
        from database.queries import get_setting, get_user_language

        uid: int | None = None
        if isinstance(event, Message) and event.from_user:
            uid = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            uid = event.from_user.id
        if uid is not None and uid in config.admin_ids_list:
            return await handler(event, data)

        if (await get_setting("maintenance_mode") or "0").strip() == "1":
            lang = "ru"
            if uid is not None:
                try:
                    lang = await get_user_language(uid)
                except Exception:
                    lang = "ru"
            t = data.get("t")
            if callable(t):
                text = t("maintenance_on")
            else:
                text = get_locale_string(lang if lang in ("ru", "tj") else "ru", "maintenance_on")
            if isinstance(event, Message):
                await event.answer(text)
            elif isinstance(event, CallbackQuery):
                await event.answer(text, show_alert=True)
            return None

        return await handler(event, data)

# ✅ ГОТОВО: middlewares/maintenance.py
