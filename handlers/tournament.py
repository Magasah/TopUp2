from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database import queries as db

router = Router()


class TournamentRegStates(StatesGroup):
    waiting_nickname = State()


@router.callback_query(F.data == "ff_tournaments")
async def ff_tournaments(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    await state.clear()
    rows = await db.list_tournaments_by_status("open")
    if not rows:
        await callback.message.answer(
            t("tournament_list_empty"),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=t("back"), callback_data="ff_choose_category")]
                ]
            ),
        )
        return
    kb_rows: list[list[InlineKeyboardButton]] = []
    for tr in rows:
        tid = int(tr["id"])
        title = str(tr.get("title") or f"#{tid}")
        n = await db.count_tournament_registrations(tid)
        max_p = int(tr.get("max_players") or 0)
        kb_rows.append(
            [
                InlineKeyboardButton(
                    text=f"🏆 {title} ({n}/{max_p})",
                    callback_data=f"tournament_view_{tid}",
                )
            ]
        )
    kb_rows.append(
        [InlineKeyboardButton(text=t("back"), callback_data="ff_choose_category")]
    )
    await callback.message.answer(
        t("tournament_pick"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
    )


@router.callback_query(F.data.startswith("tournament_view_"))
async def tournament_view(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    tid = int((callback.data or "").removeprefix("tournament_view_"))
    tr = await db.get_tournament(tid)
    if not tr or str(tr.get("status")) != "open":
        await callback.message.answer(t("tournament_list_empty"))
        return
    uid = callback.from_user.id
    n = await db.count_tournament_registrations(tid)
    max_p = int(tr.get("max_players") or 0)
    already = await db.is_user_registered_tournament(tid, uid)
    lines = [
        f"<b>{tr.get('title')}</b>",
        "────────────────────",
        str(tr.get("description") or ""),
        "────────────────────",
        t("tournament_slots", current=n, max=max_p),
    ]
    rows: list[list[InlineKeyboardButton]] = []
    if already:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t("tournament_already_registered"),
                    callback_data="noop_tournament",
                )
            ]
        )
    elif n >= max_p:
        rows.append(
            [InlineKeyboardButton(text=t("tournament_full"), callback_data="noop_tournament")]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t("tournament_register_btn"),
                    callback_data=f"tournament_register_{tid}",
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(text=t("back"), callback_data="ff_tournaments")]
    )
    await callback.message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data == "noop_tournament")
async def noop_tournament(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("tournament_register_"))
async def tournament_register_start(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    tid = int((callback.data or "").removeprefix("tournament_register_"))
    tr = await db.get_tournament(tid)
    if not tr or str(tr.get("status")) != "open":
        return
    n = await db.count_tournament_registrations(tid)
    if n >= int(tr.get("max_players") or 0):
        await callback.message.answer(t("tournament_full"))
        return
    if await db.is_user_registered_tournament(tid, callback.from_user.id):
        await callback.message.answer(t("tournament_already_registered"))
        return
    await state.set_state(TournamentRegStates.waiting_nickname)
    await state.update_data(tournament_id=tid)
    await callback.message.answer(t("tournament_enter_nickname"))


@router.message(TournamentRegStates.waiting_nickname, F.text)
async def tournament_register_finish(message: Message, state: FSMContext, t) -> None:
    nick = (message.text or "").strip()
    if len(nick) < 2 or len(nick) > 64:
        await message.answer(t("tournament_invalid_nickname"))
        return
    data = await state.get_data()
    tid = int(data["tournament_id"])
    tr = await db.get_tournament(tid)
    if not tr or str(tr.get("status")) != "open":
        await state.clear()
        return
    n = await db.count_tournament_registrations(tid)
    if n >= int(tr.get("max_players") or 0):
        await message.answer(t("tournament_full"))
        await state.clear()
        return
    ok = await db.register_tournament_user(
        tid,
        message.from_user.id,
        message.from_user.username,
        nick,
    )
    await state.clear()
    if ok:
        await message.answer(
            t("tournament_register_success"),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=t("back"), callback_data="ff_choose_category")]
                ]
            ),
        )
    else:
        await message.answer(t("tournament_already_registered"))

# ✅ ГОТОВО: handlers/tournament.py
