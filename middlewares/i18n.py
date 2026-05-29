import json
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"


class I18nMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self.locales: dict[str, dict[str, str]] = {}
        for lang in ("ru", "tj"):
            path = LOCALES_DIR / f"{lang}.json"
            with path.open(encoding="utf-8") as f:
                self.locales[lang] = json.load(f)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_lang = data.get("user_lang", "ru")
        if user_lang not in self.locales:
            user_lang = "ru"

        def t(key: str, **kwargs: Any) -> str:
            text = self.locales.get(user_lang, self.locales["ru"]).get(key, key)
            for k, v in kwargs.items():
                text = text.replace("{" + k + "}", str(v))
            return text

        data["t"] = t
        return await handler(event, data)
