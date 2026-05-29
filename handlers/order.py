from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.inline import payment_kb
from utils.formatter import escape_minimal, fmt_price
from utils.tg_api import send_message

from handlers.order_flow import OrderFlow

router = Router()


@router.message(OrderFlow.game_id, F.text)
async def game_id_entered(message: Message, state: FSMContext, t) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or not (3 <= len(raw) <= 15):
        await message.answer(t("invalid_game_id"))
        return
    await state.update_data(game_account_id=raw)
    data = await state.get_data()
    await state.set_state(OrderFlow.confirm)
    summary = t(
        "order_summary",
        game=escape_minimal(str(data.get("game_name") or "")),
        product=escape_minimal(str(data.get("product_label") or "")),
        price=fmt_price(data.get("price_tjs")),
        gid=raw,
    )
    kb = InlineKeyboardBuilder()
    kb.button(text=t("confirm_yes"), callback_data="order_confirm")
    kb.button(text=t("confirm_no"), callback_data="order_cancel")
    kb.adjust(1)
    await message.answer(summary, parse_mode="HTML", reply_markup=kb.as_markup())


@router.callback_query(OrderFlow.confirm, F.data == "order_cancel")
async def order_cancel(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.answer(t("order_cancelled"))


@router.callback_query(OrderFlow.confirm, F.data == "order_confirm")
async def order_confirm(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    await state.set_state(OrderFlow.waiting_receipt)
    chat_id = callback.message.chat.id
    try:
        await callback.message.delete()
    except Exception:
        pass
    await send_message(
        chat_id,
        t("payment_title"),
        payment_kb(t),
    )
