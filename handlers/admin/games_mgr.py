from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database.queries import delete_game, get_all_games, insert_game, update_game

router = Router()


class GameAdmin(StatesGroup):
    name = State()
    emoji = State()
    cover = State()


class GameEditCover(StatesGroup):
    waiting = State()


@router.callback_query(F.data == "adm_games_menu")
async def games_menu(callback: CallbackQuery, t) -> None:
    await callback.answer()
    games = await get_all_games(active_only=False)
    rows = []
    for g in games:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"✏️ {g['name']}",
                    callback_data=f"adm_gedit_{g['id']}",
                ),
                InlineKeyboardButton(
                    text=f"🗑 {g['id']}",
                    callback_data=f"adm_gdel_{g['id']}",
                ),
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=t("game_add"),
                callback_data="adm_gadd",
            )
        ]
    )
    rows.append(
        [InlineKeyboardButton(text=t("back"), callback_data="adm_back_panel")]
    )
    await callback.message.edit_text(
        t("games_list"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "adm_gadd")
async def game_add(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    await state.set_state(GameAdmin.name)
    await callback.message.answer(t("enter_game_name"))


@router.message(GameAdmin.name, F.text)
async def game_name(message: Message, state: FSMContext, t) -> None:
    await state.update_data(name=(message.text or "").strip())
    await state.set_state(GameAdmin.emoji)
    await message.answer(t("enter_game_emoji"))


@router.message(GameAdmin.emoji, F.text)
async def game_emoji(message: Message, state: FSMContext, t) -> None:
    await state.update_data(emoji=(message.text or "").strip())
    await state.set_state(GameAdmin.cover)
    await message.answer(t("send_cover_or_skip"))


@router.message(GameAdmin.cover, F.text)
async def game_cover_text(message: Message, state: FSMContext, t) -> None:
    data = await state.get_data()
    if (message.text or "").strip() != "-":
        await message.answer(t("send_cover_or_skip"))
        return
    gid = await insert_game(data["name"], data["emoji"], None)
    await state.clear()
    await message.answer(t("game_saved") + f" (id={gid})")


@router.message(GameAdmin.cover, F.photo)
async def game_cover_photo(message: Message, state: FSMContext, t) -> None:
    data = await state.get_data()
    fid = message.photo[-1].file_id
    gid = await insert_game(data["name"], data["emoji"], fid)
    await state.clear()
    await message.answer(t("game_saved") + f" (id={gid})")


@router.callback_query(F.data.startswith("adm_gdel_"))
async def game_del(callback: CallbackQuery, t) -> None:
    await callback.answer()
    gid = int((callback.data or "").removeprefix("adm_gdel_"))
    await delete_game(gid)
    await callback.message.answer(t("game_deleted"))


@router.callback_query(F.data.startswith("adm_gedit_"))
async def game_edit_start(
    callback: CallbackQuery,
    state: FSMContext,
    t,
) -> None:
    await callback.answer()
    gid = int((callback.data or "").removeprefix("adm_gedit_"))
    await state.set_state(GameEditCover.waiting)
    await state.update_data(game_id=gid)
    await callback.message.answer(
        t("send_cover_or_skip") + f"\n(game id: {gid})",
    )


@router.message(GameEditCover.waiting, F.text)
async def game_edit_cover_text(message: Message, state: FSMContext, t) -> None:
    if (message.text or "").strip() != "-":
        await message.answer(t("send_cover_or_skip"))
        return
    data = await state.get_data()
    gid = int(data["game_id"])
    await update_game(gid, cover_path=None)
    await state.clear()
    await message.answer(t("game_saved"))


@router.message(GameEditCover.waiting, F.photo)
async def game_edit_cover_photo(message: Message, state: FSMContext, t) -> None:
    data = await state.get_data()
    gid = int(data["game_id"])
    fid = message.photo[-1].file_id
    await update_game(gid, cover_path=fid)
    await state.clear()
    await message.answer(t("game_saved"))
