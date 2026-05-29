from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from config import config
from database.queries import get_game_by_id, get_game_by_name, get_product_by_id, get_products_by_game
from keyboards.inline import products_kb
from utils.tg_api import send_photo

from handlers.order_flow import OrderFlow

router = Router()


def _ff_categories_kb(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("ff_cat_donate"), callback_data="ff_donate"),
                InlineKeyboardButton(
                    text=t("ff_cat_donate_indonesia"),
                    callback_data="ff_donate_indonesia",
                ),
            ],
            [InlineKeyboardButton(text=t("back"), callback_data="main_menu")],
        ]
    )


@router.callback_query(F.data == "other_games")
async def other_games(callback: CallbackQuery, t) -> None:
    await callback.answer()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Standoff 2", callback_data="standoff_start")],
            [InlineKeyboardButton(text="🤖 ИИ Подписки", callback_data="ai_subs_start")],
            [InlineKeyboardButton(text=t("other_menu_btn"), callback_data="other_menu")],
            [InlineKeyboardButton(text=t("back"), callback_data="main_menu")],
        ]
    )
    await callback.message.answer(
        f"{t('other_games')}\n────────────────────\n{t('choose_action')}",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("game_"))
async def on_game(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    gid = int(callback.data.split("_", 1)[1])
    game = await get_game_by_id(gid)
    if not game or not game.get("is_active"):
        return
    game_name = str(game.get("name") or "").lower()
    if game_name == "black russia":
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            t("br_welcome"),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=t("br_topup_btn"), callback_data="br_topup_start")],
                    [InlineKeyboardButton(text=t("back"), callback_data="main_menu")],
                ]
            ),
        )
        return
    if game_name == "free fire":
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            t("ff_choose_category"),
            reply_markup=_ff_categories_kb(t),
        )
        return
    products = await get_products_by_game(gid)
    photo = config.game_listing_cover(
        str(game.get("name") or ""),
        game.get("cover_path"),
    )
    cap = f"{game.get('emoji') or ''} <b>{game.get('name')}</b>\n\n" + t("pick_product")
    chat_id = callback.message.chat.id
    try:
        await callback.message.delete()
    except Exception:
        pass
    await send_photo(
        chat_id,
        photo,
        cap,
        products_kb(products, t, back_cb="main_menu"),
    )


async def _ff_donate_list(
    callback: CallbackQuery,
    t,
    *,
    subcategory: str,
    title_suffix: str,
) -> None:
    game = await get_game_by_name("Free Fire")
    if not game:
        return
    products = await get_products_by_game(int(game["id"]), subcategory=subcategory)
    photo = config.game_listing_cover("Free Fire", game.get("cover_path"))
    try:
        await callback.message.delete()
    except Exception:
        pass
    cap = f"🔥 <b>Free Fire</b> — {title_suffix}\n\n{t('pick_product')}"
    await send_photo(
        callback.message.chat.id,
        photo,
        cap,
        products_kb(products, t, back_cb="ff_choose_category"),
    )


@router.callback_query(F.data == "ff_donate")
async def ff_donate(callback: CallbackQuery, t) -> None:
    await callback.answer()
    await _ff_donate_list(callback, t, subcategory="cis", title_suffix=t("ff_donate_cis_title"))


@router.callback_query(F.data == "ff_donate_indonesia")
async def ff_donate_indonesia(callback: CallbackQuery, t) -> None:
    await callback.answer()
    await _ff_donate_list(
        callback,
        t,
        subcategory="indonesia",
        title_suffix=t("ff_donate_indonesia_title"),
    )


@router.callback_query(F.data.in_(("ff_choose_category", "ff_back_categories")))
async def ff_choose_category_handler(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(t("ff_choose_category"), reply_markup=_ff_categories_kb(t))


def _is_shop_product_pick(data: str | None) -> bool:
    """Только выбор товара в витрине: product_123. Не трогать admin product_edit_ / product_add_ / product_delete_."""
    if not data or not data.startswith("product_"):
        return False
    return data.removeprefix("product_").isdigit()


@router.callback_query(lambda c: _is_shop_product_pick(c.data))
async def on_product(callback: CallbackQuery, state: FSMContext, t) -> None:
    await callback.answer()
    pid = int((callback.data or "").removeprefix("product_"))
    product = await get_product_by_id(pid)
    if not product or not product.get("is_active"):
        return
    game = await get_game_by_id(int(product["game_id"]))
    if not game:
        return

    await state.set_state(OrderFlow.game_id)
    await state.update_data(
        product_id=pid,
        game_id=game["id"],
        game_name=game["name"],
        product_label=product["label"],
        price_tjs=float(product["price_tjs"]),
    )

    chat_id = callback.message.chat.id
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.bot.send_message(
        chat_id,
        t("enter_game_id"),
        parse_mode="HTML",
    )

# ✅ ГОТОВО: handlers/games.py
