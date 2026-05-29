from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database.queries import (
    delete_product,
    get_all_games,
    get_game_by_id,
    get_product_by_id,
    get_products_by_game,
    insert_product,
    update_product,
)
from utils.formatter import fmt_price, format_product_label

router = Router()


class ProductAdmin(StatesGroup):
    add_label = State()
    add_price = State()
    edit_label = State()
    edit_price = State()


async def _open_products_for_game(callback: CallbackQuery, gid: int, t) -> None:
    game = await get_game_by_id(gid)
    if not game:
        return
    products = await get_products_by_game(gid, active_only=False)
    lines = [t("products_list", game=game["name"]), ""]
    rows = []
    for p in products:
        lines.append(f"· {p['label']} — {fmt_price(p['price_tjs'])}")
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"✏️ #{p['id']}",
                    callback_data=f"adm_pedit_{p['id']}",
                ),
                InlineKeyboardButton(
                    text=f"🗑 #{p['id']}",
                    callback_data=f"adm_pdel_{p['id']}",
                ),
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=t("product_add"),
                callback_data=f"adm_padd_{gid}",
            )
        ]
    )
    rows.append(
        [InlineKeyboardButton(text=t("back"), callback_data="adm_products_menu")]
    )
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "adm_products_menu")
async def products_menu(callback: CallbackQuery, t) -> None:
    await callback.answer()
    games = await get_all_games(active_only=False)
    rows = [
        [
            InlineKeyboardButton(
                text=f"{g.get('emoji') or ''} {g['name']}".strip(),
                callback_data=f"adm_pg_{g['id']}",
            )
        ]
        for g in games
    ]
    rows.append(
        [InlineKeyboardButton(text=t("back"), callback_data="adm_back_panel")]
    )
    await callback.message.edit_text(
        t("products_pick_game"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data.startswith("adm_pg_"))
async def products_for_game(callback: CallbackQuery, t) -> None:
    await callback.answer()
    gid = int((callback.data or "").removeprefix("adm_pg_"))
    await _open_products_for_game(callback, gid, t)


@router.callback_query(F.data == "adm_pg_quick_ff")
async def products_quick_ff(callback: CallbackQuery, t) -> None:
    await callback.answer()
    games = await get_all_games(active_only=False)
    ff = next((g for g in games if str(g.get("name", "")).lower() == "free fire"), None)
    if not ff:
        await callback.message.answer("Free Fire не найден в списке игр.")
        return
    await _open_products_for_game(callback, int(ff["id"]), t)


@router.callback_query(F.data == "adm_pg_quick_pubg")
async def products_quick_pubg(callback: CallbackQuery, t) -> None:
    await callback.answer()
    games = await get_all_games(active_only=False)
    pubg = next(
        (g for g in games if str(g.get("name", "")).lower() == "pubg mobile"),
        None,
    )
    if not pubg:
        await callback.message.answer("PUBG Mobile не найден в списке игр.")
        return
    await _open_products_for_game(callback, int(pubg["id"]), t)


@router.callback_query(F.data.startswith("adm_padd_"))
async def product_add_start(
    callback: CallbackQuery,
    state: FSMContext,
    t,
) -> None:
    await callback.answer()
    gid = int((callback.data or "").removeprefix("adm_padd_"))
    await state.set_state(ProductAdmin.add_label)
    await state.update_data(game_id=gid)
    await callback.message.answer(t("enter_product_label"))


@router.message(ProductAdmin.add_label, F.text)
async def product_add_label(message: Message, state: FSMContext, t) -> None:
    await state.update_data(raw_label=(message.text or "").strip())
    await state.set_state(ProductAdmin.add_price)
    await message.answer(t("enter_product_price"))


@router.message(ProductAdmin.add_price, F.text)
async def product_add_price(message: Message, state: FSMContext, t) -> None:
    raw = (message.text or "").strip().replace(",", ".")
    try:
        price = float(raw)
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer(t("invalid_price"))
        return
    data = await state.get_data()
    gid = int(data["game_id"])
    game = await get_game_by_id(gid)
    label = format_product_label(str(data["raw_label"]), game["name"] if game else "")
    await insert_product(gid, label, price)
    await state.clear()
    await message.answer(t("product_saved"))


@router.callback_query(F.data.startswith("adm_pdel_"))
async def product_del(callback: CallbackQuery, t) -> None:
    await callback.answer()
    pid = int((callback.data or "").removeprefix("adm_pdel_"))
    await delete_product(pid)
    await callback.message.answer(t("product_deleted"))


@router.callback_query(F.data.startswith("adm_pedit_"))
async def product_edit_start(
    callback: CallbackQuery,
    state: FSMContext,
    t,
) -> None:
    await callback.answer()
    pid = int((callback.data or "").removeprefix("adm_pedit_"))
    p = await get_product_by_id(pid)
    if not p:
        return
    await state.set_state(ProductAdmin.edit_label)
    await state.update_data(product_id=pid, game_id=p["game_id"])
    await callback.message.answer(
        t("enter_product_label") + f"\n\nТекущее: {p['label']}",
    )


@router.message(ProductAdmin.edit_label, F.text)
async def product_edit_label(message: Message, state: FSMContext, t) -> None:
    await state.update_data(raw_label=(message.text or "").strip())
    await state.set_state(ProductAdmin.edit_price)
    await message.answer(t("enter_product_price"))


@router.message(ProductAdmin.edit_price, F.text)
async def product_edit_price(message: Message, state: FSMContext, t) -> None:
    raw = (message.text or "").strip().replace(",", ".")
    try:
        price = float(raw)
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer(t("invalid_price"))
        return
    data = await state.get_data()
    pid = int(data["product_id"])
    gid = int(data["game_id"])
    game = await get_game_by_id(gid)
    label = format_product_label(str(data["raw_label"]), game["name"] if game else "")
    await update_product(pid, label=label, price_tjs=price)
    await state.clear()
    await message.answer(t("product_saved"))
