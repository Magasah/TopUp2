import asyncio

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database.queries import get_all_users_tg_ids, insert_broadcast

router = Router()

# Пауза между отправками, чтобы не упереться в лимиты Telegram (~30 msg/sec).
SEND_DELAY = 0.05


class BroadcastStates(StatesGroup):
    waiting_text = State()


def _confirm_kb(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("broadcast_send"),
                    callback_data="adm_broadcast_confirm",
                ),
                InlineKeyboardButton(
                    text=t("broadcast_cancel"),
                    callback_data="adm_broadcast_cancel",
                ),
            ]
        ]
    )


@router.callback_query(F.data == "adm_broadcast_start")
async def broadcast_start(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    await state.set_state(BroadcastStates.waiting_text)
    await callback.message.answer(
        t("broadcast_enter") + "\n\n📸 Можно отправить фото с подписью."
    )


@router.message(BroadcastStates.waiting_text, F.photo)
async def broadcast_got_photo(message: Message, state: FSMContext, t) -> None:
    caption = message.caption or ""
    await state.update_data(
        broadcast_photo=message.photo[-1].file_id,
        broadcast_text=caption,
    )
    await message.answer_photo(
        message.photo[-1].file_id,
        caption=t("broadcast_preview", text=caption) if caption else "📢 Предпросмотр",
        reply_markup=_confirm_kb(t),
    )


@router.message(BroadcastStates.waiting_text, F.text)
async def broadcast_got_text(message: Message, state: FSMContext, t) -> None:
    text = message.text or ""
    await state.update_data(broadcast_text=text, broadcast_photo=None)
    await message.answer(t("broadcast_preview", text=text), reply_markup=_confirm_kb(t))


@router.callback_query(F.data == "adm_broadcast_cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    await state.clear()
    try:
        await callback.message.edit_text(t("order_cancelled"))
    except Exception:
        await callback.message.answer(t("order_cancelled"))


@router.callback_query(F.data == "adm_broadcast_confirm")
async def broadcast_confirm(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    data = await state.get_data()
    text = data.get("broadcast_text") or ""
    photo = data.get("broadcast_photo")
    await state.clear()

    users = await get_all_users_tg_ids()
    ok = 0
    for uid in users:
        try:
            if photo:
                await callback.bot.send_photo(
                    uid, photo, caption=text or None, parse_mode="HTML"
                )
            else:
                await callback.bot.send_message(uid, text, parse_mode="HTML")
            ok += 1
        except Exception:
            continue
        await asyncio.sleep(SEND_DELAY)

    await insert_broadcast(text or "[photo]", ok)
    await callback.message.answer(t("broadcast_done", n=ok, total=len(users)))
