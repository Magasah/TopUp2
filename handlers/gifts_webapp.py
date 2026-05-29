"""
Мини-приложение «Подарки (NFT)» (React в каталоге webapp/gifts, деплой на Vercel).

Связь с ботом:
- В .env задайте GIFTS_WEBAPP_URL — полный https://... адрес после деплоя.
- В BotFather для бота добавьте домен Vercel (Mini Apps / Web App domain).
- Имя продавца для кнопки «Купить» передаётся в URL как ?seller=... из ADMIN_TG
  (если это @username); иначе используйте VITE_SELLER_USERNAME в настройках Vercel.
"""

from __future__ import annotations

from urllib.parse import quote

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, WebAppInfo

from config import config

router = Router(name="gifts_webapp")


def gifts_webapp_launch_url() -> str:
    """Полный URL Mini App с опциональным ?seller=username из ADMIN_TG."""
    base = (config.gifts_webapp_url or "").strip().rstrip("/")
    if not base:
        return ""
    admin = (config.ADMIN_TG or "").strip()
    if admin.lstrip("-").isdigit():
        return base
    uname = admin.lstrip("@")
    if not uname or uname.lstrip("-").isdigit():
        return base
    join = "&" if "?" in base else "?"
    return f"{base}{join}seller={quote(uname, safe='')}"


def append_gifts_menu_row(rows: list[list[InlineKeyboardButton]]) -> None:
    """Добавляет кнопку Web App или заглушку в меню «Другое»."""
    launch = gifts_webapp_launch_url()
    if launch:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🎁 Подарки (NFT)",
                    web_app=WebAppInfo(url=launch),
                )
            ]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🎁 Подарки (NFT)",
                    callback_data="gifts_webapp_unconfigured",
                )
            ]
        )


@router.callback_query(F.data == "gifts_webapp_unconfigured")
async def gifts_webapp_unconfigured(callback: CallbackQuery, t) -> None:
    await callback.answer(t("gifts_webapp_configure_alert"), show_alert=True)
