import math
import re
from typing import Optional

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database import queries as db
from database.queries import count_recent_orders_for_user, get_game_by_name, get_product_by_id, get_products_by_game
from keyboards.inline import payment_kb, receipt_cancel_markup
from utils.assets import get_game_photo
from utils.formatter import fmt_price
from utils.notify import notify_admins_typed_order
from utils.receipt_checker import append_receipt_note, check_receipt, register_receipt
from utils.payment_flow import show_payment_methods, show_requisites

router = Router()

MAX_ORDERS_PER_HOUR = 3

# Ручной ввод: та же база, что пакеты (ggsel ~1199₽/1000 gold + наценка), ~9.8₽ за 1 смн
_STANDOFF_MANUAL_TJS_PER_GOLD = 0.133
_STANDOFF_MANUAL_MIN_TJS = 19


class StandoffFlow(StatesGroup):
    waiting_manual_gold = State()
    waiting_game_id = State()
    waiting_confirm = State()
    waiting_payment_method = State()
    waiting_receipt = State()


def _standoff_kb(products: list, t) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for p in products:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{p['label']} — {fmt_price(p['price_tjs'])}",
                    callback_data=f"standoff_product_{p['id']}",
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(text=t("standoff_manual_gold_btn"), callback_data="standoff_manual")]
    )
    rows.append([InlineKeyboardButton(text=t("back"), callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _gold_from_label(label: str) -> Optional[int]:
    m = re.search(r"(\d+)", str(label or ""))
    return int(m.group(1)) if m else None


@router.callback_query(F.data == "standoff_start")
async def standoff_start(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    await state.clear()
    game = await get_game_by_name("Standoff 2")
    if not game:
        await callback.message.answer(t("standoff_unavailable"))
        return
    products = await get_products_by_game(int(game["id"]))
    photo = get_game_photo("standoff2")
    cap = t("standoff_welcome")
    chat_id = callback.from_user.id
    kb = _standoff_kb(products, t)
    if photo:
        await callback.bot.send_photo(
            chat_id,
            photo=photo,
            caption=cap,
            parse_mode="HTML",
            reply_markup=kb,
        )
    else:
        await callback.message.answer(cap, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "standoff_manual")
async def standoff_manual(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    await state.set_state(StandoffFlow.waiting_manual_gold)
    await callback.message.answer(t("standoff_enter_gold_amount"))


@router.message(StandoffFlow.waiting_manual_gold, F.text)
async def standoff_manual_gold_enter(message: Message, state: FSMContext, t) -> None:
    raw = (message.text or "").strip().replace(" ", "")
    if not raw.isdigit():
        await message.answer(t("standoff_invalid_gold"))
        return
    gold = int(raw)
    if gold < 10:
        await message.answer(t("standoff_invalid_gold"))
        return
    price = float(
        max(_STANDOFF_MANUAL_MIN_TJS, math.floor(gold * _STANDOFF_MANUAL_TJS_PER_GOLD))
    )
    if price < 1:
        await message.answer(t("standoff_invalid_gold"))
        return
    await state.update_data(
        product_label=t("standoff_manual_label", gold=gold),
        price_tjs=price,
        gold_amount=gold,
        is_manual=1,
    )
    await state.set_state(StandoffFlow.waiting_game_id)
    await message.answer(t("standoff_enter_id"))


@router.callback_query(F.data.startswith("standoff_product_"))
async def standoff_product_pick(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    pid = int(callback.data.rsplit("_", 1)[1])
    product = await get_product_by_id(pid)
    if not product:
        return
    g = _gold_from_label(product.get("label"))
    await state.update_data(
        product_label=str(product.get("label") or ""),
        price_tjs=float(product.get("price_tjs") or 0),
        gold_amount=g,
        is_manual=0,
    )
    await state.set_state(StandoffFlow.waiting_game_id)
    await callback.message.answer(t("standoff_enter_id"))


@router.message(StandoffFlow.waiting_game_id, F.text)
async def standoff_game_id(message: Message, state: FSMContext, t) -> None:
    gid = (message.text or "").strip()
    if not gid.isdigit() or len(gid) < 4:
        await message.answer(t("standoff_invalid_id"))
        return
    data = await state.get_data()
    await state.update_data(game_account_id=gid)
    await state.set_state(StandoffFlow.waiting_confirm)
    await message.answer(
        t(
            "standoff_order_summary",
            product=data["product_label"],
            price=fmt_price(float(data["price_tjs"])),
            gid=gid,
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=t("confirm_yes"), callback_data="standoff_confirm")],
                [InlineKeyboardButton(text=t("confirm_no"), callback_data="standoff_cancel")],
            ]
        ),
    )


@router.callback_query(F.data == "standoff_cancel", StateFilter("*"))
async def standoff_cancel(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    st = await state.get_state()
    if st and str(st).startswith("StandoffFlow:"):
        await state.clear()
        await callback.message.answer(t("order_cancelled"))


@router.callback_query(F.data == "standoff_confirm", StandoffFlow.waiting_confirm)
async def standoff_confirm(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    data = await state.get_data()
    await show_payment_methods(callback.from_user.id, str(float(data["price_tjs"])), "смн")
    await state.set_state(StandoffFlow.waiting_payment_method)


@router.callback_query(
    F.data.in_(("pay_dc", "pay_alif")),
    StandoffFlow.waiting_payment_method,
)
async def standoff_payment(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    data = await state.get_data()
    key = callback.data or ""
    if key == "pay_alif":
        method = "alif"
    else:
        method = "dc"
    await state.update_data(payment_method=method)
    await show_requisites(
        callback.from_user.id,
        key,
        str(float(data.get("price_tjs") or 0)),
        "смн",
    )
    await state.set_state(StandoffFlow.waiting_receipt)
    await callback.message.answer(
        t("receipt_wait_photo"),
        reply_markup=receipt_cancel_markup(t),
    )


@router.callback_query(StandoffFlow.waiting_receipt, F.data == "cancel_payment")
async def standoff_cancel_pay(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    from config import config
    from database.queries import get_all_games
    from keyboards.inline import main_menu_kb
    from utils.tg_api import send_photo

    games = await get_all_games()
    await send_photo(
        callback.message.chat.id,
        config.welcome_photo,
        t("welcome", name=callback.from_user.first_name or ""),
        main_menu_kb(games, t),
    )


@router.message(StandoffFlow.waiting_receipt, F.photo)
async def standoff_receipt(message: Message, state: FSMContext, t) -> None:
    data = await state.get_data()
    pm = data.get("payment_method")
    if not pm:
        await message.answer(t("payment_title"), reply_markup=payment_kb(t))
        return
    uid = message.from_user.id
    if await count_recent_orders_for_user(uid) >= MAX_ORDERS_PER_HOUR:
        await message.answer(t("order_rate_limit"))
        await state.clear()
        return
    is_dup, dup_text = await check_receipt(message, "standoff", t)
    if is_dup:
        await message.answer(dup_text, reply_markup=receipt_cancel_markup(t), parse_mode="HTML")
        return

    method = str(pm)
    photo = message.photo[-1]
    file_id = photo.file_id
    oid = await db.create_standoff_order(
        user_tg_id=uid,
        username=message.from_user.username,
        product_label=str(data.get("product_label") or ""),
        price_tjs=float(data.get("price_tjs") or 0),
        game_account_id=str(data.get("game_account_id") or ""),
        payment_method=method,
        receipt_file_id=file_id,
        gold_amount=data.get("gold_amount"),
        is_manual=int(data.get("is_manual") or 0),
    )
    await register_receipt(
        photo.file_unique_id, file_id, uid, "standoff", oid
    )
    await state.clear()
    await message.answer(t("order_created", oid=oid))
    order = await db.get_standoff_order(oid)
    if order:
        cap = (
            f"🎯 <b>Standoff 2</b> заказ #{oid}\n"
            f"─────────────────────\n"
            f"👤 @{order.get('username') or order['user_tg_id']}\n"
            f"📦 {order.get('product_label')}\n"
            f"💰 {order.get('price_tjs')} смн | 💳 {order.get('payment_method')}\n"
            f"🆔 ID: {order.get('game_account_id')}\n"
            f"🕐 {order.get('created_at')}"
        )
        cap = append_receipt_note(cap, t)
        await notify_admins_typed_order(message.bot, "standoff", order, cap)


@router.message(StandoffFlow.waiting_receipt, F.text)
async def standoff_need_photo(message: Message, t) -> None:
    await message.answer(t("receipt_need_photo"))

# ✅ ГОТОВО: handlers/standoff.py
