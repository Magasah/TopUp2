from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database.queries import add_required_channel, delete_required_channel, get_required_channels

router = Router()


class SubChannelsState(StatesGroup):
    waiting_channel_ref = State()


def _menu_kb(rows: list[dict]) -> InlineKeyboardMarkup:
    kb_rows: list[list[InlineKeyboardButton]] = []
    for row in rows:
        kb_rows.append(
            [
                InlineKeyboardButton(
                    text=f"🗑 {row['channel_ref']}",
                    callback_data=f"req_sub_del_{row['id']}",
                )
            ]
        )
    kb_rows.append([InlineKeyboardButton(text="➕ Добавить канал", callback_data="req_sub_add")])
    kb_rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="adm_back_panel")])
    return InlineKeyboardMarkup(inline_keyboard=kb_rows)


@router.callback_query(F.data == "admin_required_subs")
async def required_subs_menu(callback: CallbackQuery, t) -> None:
    await callback.answer()
    rows = await get_required_channels()
    lines = [t("req_sub_title"), "────────────────────", t("req_sub_hint")]
    if rows:
        lines.append("")
        lines.extend([f"• {r['channel_ref']}" for r in rows])
    else:
        lines.append("\n" + t("req_sub_empty"))
    await callback.message.edit_text("\n".join(lines), reply_markup=_menu_kb(rows))


@router.callback_query(F.data == "req_sub_add")
async def required_subs_add_start(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    await state.set_state(SubChannelsState.waiting_channel_ref)
    await callback.message.answer(t("req_sub_enter"))


@router.message(SubChannelsState.waiting_channel_ref, F.text)
async def required_subs_add_finish(message: Message, state: FSMContext, t) -> None:
    raw = (message.text or "").strip()
    channel_ref = raw
    if raw.startswith("https://t.me/"):
        channel_ref = "@" + raw.removeprefix("https://t.me/").strip("/").split("/")[-1]
    await add_required_channel(channel_ref)
    await state.clear()
    await message.answer(t("req_sub_added", channel=channel_ref))


@router.callback_query(F.data.startswith("req_sub_del_"))
async def required_subs_delete(callback: CallbackQuery, t) -> None:
    await callback.answer()
    rid = int((callback.data or "").removeprefix("req_sub_del_"))
    await delete_required_channel(rid)
    rows = await get_required_channels()
    await callback.message.edit_reply_markup(reply_markup=_menu_kb(rows))
    await callback.answer(t("req_sub_deleted"))
