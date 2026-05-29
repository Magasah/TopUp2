from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from utils.admins import is_admin


class AdminOnlyMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        t = data.get("t")
        uid = None
        if isinstance(event, Message) and event.from_user:
            uid = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            uid = event.from_user.id
        if not is_admin(uid):
            deny = t("admin_no_access") if t else "⛔ Нет доступа."
            if isinstance(event, Message):
                await event.answer(deny)
            elif isinstance(event, CallbackQuery):
                await event.answer(deny, show_alert=True)
            return
        return await handler(event, data)
