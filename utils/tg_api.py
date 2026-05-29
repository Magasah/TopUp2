import json
import os
from typing import Any, Optional

import aiofiles
import aiohttp

from config import config

BASE = f"https://api.telegram.org/bot{config.BOT_TOKEN}"


async def send_message(
    chat_id: int,
    text: str,
    keyboard: Optional[dict[str, Any]] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    if keyboard:
        payload["reply_markup"] = keyboard
    payload.update(kwargs)
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE}/sendMessage", json=payload) as resp:
            return await resp.json()


async def send_photo(
    chat_id: int,
    photo: str,
    caption: str,
    keyboard: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    photo: локальный путь к файлу или file_id Telegram.
    """
    if photo and os.path.isfile(photo):
        data = aiohttp.FormData()
        data.add_field("chat_id", str(chat_id))
        data.add_field("caption", caption)
        data.add_field("parse_mode", "HTML")
        if keyboard:
            data.add_field("reply_markup", json.dumps(keyboard))
        async with aiofiles.open(photo, "rb") as f:
            raw = await f.read()
        data.add_field(
            "photo",
            raw,
            filename=os.path.basename(photo),
            content_type="image/jpeg",
        )
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BASE}/sendPhoto", data=data) as resp:
                return await resp.json()

    if photo:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "photo": photo,
            "caption": caption,
            "parse_mode": "HTML",
        }
        if keyboard:
            payload["reply_markup"] = keyboard
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BASE}/sendPhoto", json=payload) as resp:
                return await resp.json()

    return await send_message(chat_id, caption, keyboard)


async def answer_callback(callback_query_id: str, text: str = "") -> dict[str, Any]:
    payload = {"callback_query_id": callback_query_id, "text": text}
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE}/answerCallbackQuery", json=payload) as resp:
            return await resp.json()


async def delete_message(chat_id: int, message_id: int) -> dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE}/deleteMessage",
            json={"chat_id": chat_id, "message_id": message_id},
        ) as resp:
            return await resp.json()


async def copy_message(
    chat_id: int,
    from_chat_id: int,
    message_id: int,
) -> dict[str, Any]:
    payload = {
        "chat_id": chat_id,
        "from_chat_id": from_chat_id,
        "message_id": message_id,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE}/copyMessage", json=payload) as resp:
            return await resp.json()
