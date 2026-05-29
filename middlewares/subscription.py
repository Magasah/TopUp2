from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from config import config
from database.queries import get_required_channels
from keyboards.inline import subscription_kb
from utils.admins import is_admin
from utils.tg_api import send_message

_SUB_CHECK_CALLBACKS = frozenset({"check_subscription", "check_sub"})


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        bot = data["bot"]
        t = data["t"]

        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if is_admin(user_id):
            return await handler(event, data)

        if user_id:
            try:
                required_refs: list[str] = []
                rows = await get_required_channels()
                required_refs.extend([str(r["channel_ref"]) for r in rows if r.get("channel_ref")])
                if not required_refs:
                    required_refs.append(config.channel_id_member_check)

                not_subscribed = False
                for channel_ref in required_refs:
                    member = await bot.get_chat_member(channel_ref, user_id)
                    if member.status in ("left", "kicked"):
                        not_subscribed = True
                        break

                if not_subscribed:
                    kb = subscription_kb(t)
                    if isinstance(event, Message):
                        await send_message(
                            user_id,
                            t("subscription_prompt"),
                            kb,
                        )
                    elif isinstance(event, CallbackQuery):
                        if event.data in _SUB_CHECK_CALLBACKS:
                            return await handler(event, data)
                        await send_message(
                            user_id,
                            t("subscription_prompt"),
                            kb,
                        )
                    return
            except Exception:
                pass
        return await handler(event, data)

# ✅ ГОТОВО: middlewares/subscription.py
