from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, TelegramObject


class StateGuardMiddleware(BaseMiddleware):
    """
    If user sends a command while being inside any FSM flow,
    drop the current flow first so command handlers don't conflict
    with state-specific text/photo handlers.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text and event.text.startswith("/"):
            state: FSMContext | None = data.get("state")
            if state is not None:
                current_state = await state.get_state()
                if current_state:
                    await state.clear()
        return await handler(event, data)

