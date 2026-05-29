from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from database.queries import antispam_check
from utils.admins import is_admin

_last_warn_ts: dict[int, float] = {}


class AntiSpamMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        t = data.get("t")
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if is_admin(user_id):
            return await handler(event, data)

        if isinstance(event, Message):
            text = (event.text or event.caption or "").strip()
            low = text.lower()
            # Basic input hardening against oversized/suspicious payloads
            if len(text) > 1200 or any(s in low for s in ("<script", "javascript:", "drop table", "union select")):
                await event.answer("⚠️ Некорректный ввод. Упростите сообщение и повторите.")
                return

        if user_id and not antispam_check(user_id):
            now = __import__("time").time()
            # Don't spam anti-spam warning itself
            if now - _last_warn_ts.get(user_id, 0.0) < 3.0:
                return
            _last_warn_ts[user_id] = now
            if isinstance(event, Message):
                msg = (
                    t("spam_wait")
                    if t
                    else "⏳ Слишком много запросов. Подождите немного."
                )
                await event.answer(msg)
            elif isinstance(event, CallbackQuery):
                msg = (
                    t("spam_wait")
                    if t
                    else "⏳ Слишком много запросов."
                )
                await event.answer(msg, show_alert=True)
            return
        return await handler(event, data)
