from typing import Any, Callable, List

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import config
from utils.formatter import fmt_price

T = Callable[..., str]


def main_menu_kb(games: List[dict[str, Any]], t: T) -> dict[str, Any]:
    ff_id = next((g["id"] for g in games if str(g.get("name", "")).lower() == "free fire"), None)
    pubg_id = next((g["id"] for g in games if str(g.get("name", "")).lower() == "pubg mobile"), None)
    rows: List[List[dict[str, Any]]] = [
        [{"text": "🔥 Free Fire", "callback_data": f"game_{ff_id}" if ff_id else "main_menu"}],
        [{"text": "🎯 Standoff 2", "callback_data": "standoff_start"}],
        [{"text": "🎮 PUBG Mobile", "callback_data": f"game_{pubg_id}" if pubg_id else "main_menu"}],
        [{"text": t("main_settings"), "callback_data": "settings"}],
    ]
    return {"inline_keyboard": rows}


def products_kb(
    products: List[dict[str, Any]],
    t: T,
    back_cb: str = "main_menu",
) -> dict[str, Any]:
    rows: List[List[dict[str, Any]]] = []
    for p in products:
        prefix = "🔥 " if p.get("is_popular") else ("⭐ " if p.get("is_best_value") else "")
        style = (
            "danger"
            if p.get("is_popular")
            else ("success" if p.get("is_best_value") else "primary")
        )
        rows.append(
            [
                {
                    "text": f"{prefix}{p['label']} — {fmt_price(p['price_tjs'])}",
                    "callback_data": f"product_{p['id']}",
                    "style": style,
                }
            ]
        )
    rows.append(
        [{"text": t("back"), "callback_data": back_cb, "style": "primary"}]
    )
    return {"inline_keyboard": rows}


def payment_kb(t: T) -> dict[str, Any]:
    rows: List[List[dict[str, Any]]] = [
        [{"text": "🏦 DC City", "callback_data": "pay_dc", "style": "primary"}],
        [{"text": "📱 Alif Mobi", "callback_data": "pay_alif", "style": "success"}],
        [{"text": t("back"), "callback_data": "cancel_order_flow", "style": "primary"}],
    ]
    return {"inline_keyboard": rows}


def receipt_cancel_kb(t: T) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {
                    "text": t("payment_cancel_btn"),
                    "callback_data": "cancel_payment",
                    "style": "danger",
                }
            ]
        ]
    }


def receipt_cancel_markup(t: T) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(
            text=t("payment_cancel_btn"),
            callback_data="cancel_payment",
        )
    )
    return b.as_markup()


def admin_order_kb(order_id: int, user_tg_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_{order_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{order_id}"),
    )
    b.row(
        InlineKeyboardButton(
            text="💬 Написать покупателю",
            url=f"tg://user?id={user_tg_id}",
        )
    )
    return b.as_markup()


def admin_review_kb(review_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(
            text="✅ Опубликовать",
            callback_data=f"rev_pub_{review_id}",
        ),
        InlineKeyboardButton(
            text="✏️ Изменить",
            callback_data=f"rev_edit_{review_id}",
        ),
        InlineKeyboardButton(
            text="❌ Отклонить",
            callback_data=f"rev_reject_{review_id}",
        ),
    )
    return b.as_markup()


def review_moderation_kb_raw(review_id: int, t: T) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {
                    "text": t("review_publish_btn"),
                    "callback_data": f"rev_pub_{review_id}",
                    "style": "success",
                },
                {
                    "text": t("review_edit_btn"),
                    "callback_data": f"rev_edit_{review_id}",
                    "style": "primary",
                },
                {
                    "text": t("review_reject_btn"),
                    "callback_data": f"rev_reject_{review_id}",
                    "style": "danger",
                },
            ]
        ]
    }


def subscription_kb(t: T) -> dict[str, Any]:
    uname = (config.channel_subscribe_username or "telegram").strip().lstrip("@")
    return {
        "inline_keyboard": [
            [
                {
                    "text": t("subscription_channel_btn"),
                    "url": f"https://t.me/{uname}",
                    "style": "primary",
                },
                {
                    "text": t("subscription_check_btn"),
                    "callback_data": "check_sub",
                    "style": "success",
                },
            ]
        ]
    }


def review_cancel_kb(t: T) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(
            text=t("review_cancel_btn"),
            callback_data="cancel_review_flow",
        )
    )
    return b.as_markup()


def ref_admin_kb_raw(user_id: int) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {
                    "text": "✅ Принять",
                    "callback_data": f"ref_approve_{user_id}",
                    "style": "success",
                },
                {
                    "text": "❌ Отклонить",
                    "callback_data": f"ref_reject_{user_id}",
                    "style": "danger",
                },
                {
                    "text": "💬 Написать",
                    "url": f"tg://user?id={user_id}",
                    "style": "primary",
                },
            ]
        ]
    }

# ✅ ГОТОВО: keyboards/inline.py

