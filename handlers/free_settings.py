import asyncio
import html

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from database import queries as db
from handlers.ff_free_settings_data import FF_SETTINGS_DB
from utils import tg_api

router = Router()

INSTAGRAM_URL = "https://www.instagram.com/kalzen_ff/"


def detect_brand(phone_model: str) -> tuple[str, dict[str, int]]:
    model_lower = phone_model.lower()
    for brand_key, brand_data in FF_SETTINGS_DB.items():
        if brand_key == "unknown":
            continue
        for keyword in brand_data["brands"]:
            if keyword in model_lower:
                for preset in brand_data.get("presets", []):
                    for match_kw in preset["match"]:
                        if match_kw in model_lower:
                            return brand_key, preset["s"]
                return brand_key, brand_data["default"]
    return "unknown", FF_SETTINGS_DB["unknown"]["default"]


def format_settings(phone_model: str, settings: dict[str, int]) -> str:
    esc = html.escape(phone_model)

    def c(v: int) -> str:
        return f"<code>{v}</code>"

    return (
        f"🎯 Настройки Free Fire 2026\n"
        f"📱 Модель: {esc}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚙️ General        — {c(settings['general'])}\n"
        f"🔴 Red Dot        — {c(settings['red_dot'])}\n"
        f"🔭 2x Scope       — {c(settings['scope_2x'])}\n"
        f"🔭 4x Scope       — {c(settings['scope_4x'])}\n"
        f"🎯 AWM Scope      — {c(settings['awm'])}\n"
        f"👁 Free Look      — {c(settings['freelook'])}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🖲 Button Size    — {c(settings['button'])}%\n"
        f"📐 DPI             — {c(settings['dpi'])}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 Нажми на цифру чтобы скопировать!\n"
        f"⚡ @kalzen_ff — Бесплатные настройки"
    )


class FreeSettingsStates(StatesGroup):
    waiting_phone_model = State()


@router.callback_query(F.data == "ff_free_settings")
async def free_settings_start(cb: CallbackQuery, state: FSMContext, t) -> None:
    await cb.answer()
    user_id = cb.from_user.id

    can_get, hours_left = await db.can_get_free_settings(user_id)
    if not can_get:
        await tg_api.send_message(
            user_id,
            t("ff_cooldown", hours=hours_left)
            + "\n\n"
            + t("ff_sub_required")
            + "\n"
            + INSTAGRAM_URL,
            {
                "inline_keyboard": [
                    [
                        {
                            "text": t("ff_instagram_link_btn"),
                            "url": INSTAGRAM_URL,
                            "style": "primary",
                        }
                    ],
                    [{"text": t("back"), "callback_data": "ff_choose_category", "style": "primary"}],
                ]
            },
        )
        return

    await tg_api.send_message(
        user_id,
        t("ff_free_settings_title")
        + "\n"
        + "━━━━━━━━━━━━━━━━━━\n"
        + t("ff_free_settings_intro")
        + "\n\n"
        + t("ff_sub_required")
        + "\n\n"
        + t("ff_free_settings_footer"),
        {
            "inline_keyboard": [
                [
                    {
                        "text": t("ff_instagram_subscribe_btn"),
                        "url": INSTAGRAM_URL,
                        "style": "primary",
                    }
                ],
                [
                    {
                        "text": t("ff_subscribed_btn"),
                        "callback_data": "ff_settings_subscribed",
                        "style": "success",
                    }
                ],
                [{"text": t("back"), "callback_data": "ff_choose_category", "style": "primary"}],
            ]
        },
    )


@router.callback_query(F.data == "ff_settings_subscribed")
async def after_subscription(cb: CallbackQuery, state: FSMContext, t) -> None:
    await cb.answer()
    await state.set_state(FreeSettingsStates.waiting_phone_model)
    await tg_api.send_message(
        cb.from_user.id,
        t("ff_free_enter_phone"),
        {
            "inline_keyboard": [
                [{"text": t("back"), "callback_data": "ff_choose_category", "style": "primary"}]
            ]
        },
    )
    try:
        await cb.message.delete()
    except Exception:
        pass


@router.message(StateFilter(FreeSettingsStates.waiting_phone_model), F.text)
async def give_settings(msg: Message, state: FSMContext, t) -> None:
    phone_model = (msg.text or "").strip()

    if len(phone_model) < 3:
        await msg.answer(t("ff_free_model_too_short"))
        return

    await state.clear()

    brand_key, settings = detect_brand(phone_model)
    await db.save_settings_log(msg.from_user.id, phone_model, brand_key)

    extra = ""
    if brand_key == "unknown":
        extra = "\n" + t("ff_unknown_brand")

    settings_text = format_settings(phone_model, settings)
    await msg.answer(settings_text + extra, parse_mode="HTML")

    await asyncio.sleep(2)
    await msg.answer(
        t("ff_free_how_to_apply_long", url=INSTAGRAM_URL),
        parse_mode="HTML",
        reply_markup={
            "inline_keyboard": [
                [{"text": t("ff_free_main_menu_btn"), "callback_data": "main_menu", "style": "primary"}],
                [
                    {
                        "text": t("ff_free_other_products_btn"),
                        "callback_data": "ff_choose_category",
                        "style": "primary",
                    }
                ],
            ]
        },
    )


@router.message(StateFilter(FreeSettingsStates.waiting_phone_model), ~F.text)
async def wrong_model_input(msg: Message, t) -> None:
    await msg.answer(t("ff_free_wrong_input_type"))

# ✅ ГОТОВО: handlers/free_settings.py
