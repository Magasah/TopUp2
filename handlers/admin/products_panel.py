from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database import queries as db
from utils.formatter import fmt_price, format_product_label

router = Router()

# Префикс adm_prod_* — чтобы не пересекаться с витриной (product_123) и другими роутерами

# callback_key -> (заголовок в админке, имя игры в БД)
GAME_KEYS: dict[str, tuple[str, str]] = {
    "ff": ("🔥 Free Fire", "Free Fire"),
    "pubg": ("🎮 PUBG Mobile", "PUBG Mobile"),
    "standoff": ("🎯 Standoff 2", "Standoff 2"),
}

FF_REGION_LABELS = {
    "cis": "💎 СНГ",
    "indonesia": "🌴 Индонезия",
}


class ProductWizard(StatesGroup):
    waiting_label = State()
    waiting_price = State()
    waiting_popular = State()
    waiting_best_value = State()
    waiting_confirm = State()


def _game_key_from_db_name(name: str) -> str:
    n = (name or "").lower()
    if "pubg" in n:
        return "pubg"
    if "standoff" in n:
        return "standoff"
    return "ff"


def _ff_subcategory_from_product(product: dict) -> str:
    sub = (product.get("subcategory") or "cis").strip().lower()
    return "indonesia" if sub == "indonesia" else "cis"


async def _find_game_id_by_key(key: str) -> int | None:
    meta = GAME_KEYS.get(key)
    if not meta:
        return None
    game = await db.get_game_by_name(meta[1])
    return int(game["id"]) if game else None


@router.callback_query(F.data == "admin_products")
async def admin_products(callback: CallbackQuery) -> None:
    await callback.answer()
    rows = [
        [InlineKeyboardButton(text=GAME_KEYS["ff"][0], callback_data="adm_prod_pick_ff")],
        [InlineKeyboardButton(text=GAME_KEYS["pubg"][0], callback_data="adm_prod_pick_pubg")],
        [InlineKeyboardButton(text=GAME_KEYS["standoff"][0], callback_data="adm_prod_pick_standoff")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="adm_back_panel")],
    ]
    await callback.message.edit_text(
        "📦 УПРАВЛЕНИЕ ТОВАРАМИ\n"
        "─────────────────────\n"
        "Выберите игру:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data == "adm_prod_pick_ff")
async def products_ff_regions(callback: CallbackQuery) -> None:
    await callback.answer()
    rows = [
        [
            InlineKeyboardButton(
                text="💎 Настроить СНГ",
                callback_data="adm_prod_ff_cis",
            )
        ],
        [
            InlineKeyboardButton(
                text="🌴 Настроить Индонезию",
                callback_data="adm_prod_ff_indonesia",
            )
        ],
        [InlineKeyboardButton(text="◀️ Назад к играм", callback_data="admin_products")],
    ]
    await callback.message.edit_text(
        "📦 Товары — 🔥 Free Fire\n─────────────────────\nВыберите регион:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.in_({"adm_prod_ff_cis", "adm_prod_ff_indonesia"}))
async def products_ff_region(callback: CallbackQuery) -> None:
    await callback.answer()
    sub = "indonesia" if callback.data.endswith("indonesia") else "cis"
    await _render_products(callback, "ff", subcategory=sub)


@router.callback_query(F.data.startswith("adm_prod_pick_"))
async def products_game(callback: CallbackQuery) -> None:
    await callback.answer()
    key = callback.data.removeprefix("adm_prod_pick_")
    if key == "ff":
        await products_ff_regions(callback)
        return
    await _render_products(callback, key)


async def _render_products(
    callback: CallbackQuery,
    key: str,
    subcategory: str | None = None,
) -> None:
    meta = GAME_KEYS.get(key)
    if not meta:
        await callback.message.answer("Неизвестная игра.")
        return
    title, _db_name = meta
    gid = await _find_game_id_by_key(key)
    if not gid:
        await callback.message.answer("Игра не найдена в БД.")
        return
    sub = subcategory if key == "ff" else None
    products = await db.get_products_by_game(gid, active_only=False, subcategory=sub)
    region_line = ""
    if key == "ff" and sub:
        region_line = f"\nРегион: {FF_REGION_LABELS.get(sub, sub)}"
    rows = []
    for p in products:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{p['label']} — {fmt_price(p['price_tjs'])}смн",
                    callback_data=f"adm_prod_noop_{p['id']}",
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(text="✏️", callback_data=f"adm_prod_edit_{p['id']}"),
                InlineKeyboardButton(text="🗑", callback_data=f"adm_prod_del_{p['id']}"),
            ]
        )
    add_cb = f"adm_prod_add_{key}"
    if key == "ff" and sub:
        add_cb = f"adm_prod_add_{key}_{sub}"
    rows.append([InlineKeyboardButton(text="➕ Добавить товар", callback_data=add_cb)])
    back_cb = "adm_prod_pick_ff" if key == "ff" else "admin_products"
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data=back_cb)])
    await callback.message.edit_text(
        f"📦 Товары — {title}{region_line}\n─────────────────────",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("adm_prod_add_"))
async def product_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    raw = callback.data.removeprefix("adm_prod_add_")
    parts = raw.split("_", 1)
    key = parts[0]
    ff_sub = parts[1] if len(parts) > 1 and parts[1] in FF_REGION_LABELS else "cis"
    await state.set_state(ProductWizard.waiting_label)
    await state.update_data(mode="add", game_key=key, ff_subcategory=ff_sub)
    await callback.message.answer("Введите название товара:")


@router.callback_query(F.data.startswith("adm_prod_edit_"))
async def product_edit_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    pid = int(callback.data.removeprefix("adm_prod_edit_"))
    product = await db.get_product_by_id(pid)
    if not product:
        await callback.message.answer("❌ Товар не найден.")
        return
    game = await db.get_game_by_id(int(product["game_id"]))
    game_key = _game_key_from_db_name(str(game["name"])) if game else "ff"
    ff_sub = _ff_subcategory_from_product(product) if game_key == "ff" else "cis"
    await state.set_state(ProductWizard.waiting_label)
    await state.update_data(
        mode="edit",
        product_id=pid,
        game_key=game_key,
        ff_subcategory=ff_sub,
    )
    await callback.message.answer(f"Введите новое название товара:\nТекущее: {product['label']}")


@router.message(StateFilter(ProductWizard.waiting_label), F.text)
async def product_label(message: Message, state: FSMContext) -> None:
    await state.update_data(raw_label=(message.text or "").strip())
    await state.set_state(ProductWizard.waiting_price)
    await message.answer("Введите цену (например 31 или 10.5):")


@router.message(StateFilter(ProductWizard.waiting_price), F.text)
async def product_price(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").replace(",", ".").strip()
    try:
        price = float(raw)
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Неверная цена.")
        return
    await state.update_data(price=price)
    await state.set_state(ProductWizard.waiting_popular)
    await message.answer(
        "Сделать товар популярным?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Да", callback_data="adm_prod_wizpop_1"),
                    InlineKeyboardButton(text="Нет", callback_data="adm_prod_wizpop_0"),
                ]
            ]
        ),
    )


@router.callback_query(StateFilter(ProductWizard.waiting_popular), F.data.startswith("adm_prod_wizpop_"))
async def wiz_popular(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    value = 1 if callback.data.endswith("_1") else 0
    await state.update_data(is_popular=value)
    await state.set_state(ProductWizard.waiting_best_value)
    await callback.message.answer(
        "Сделать товар best value?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Да", callback_data="adm_prod_wizbest_1"),
                    InlineKeyboardButton(text="Нет", callback_data="adm_prod_wizbest_0"),
                ]
            ]
        ),
    )


@router.callback_query(StateFilter(ProductWizard.waiting_best_value), F.data.startswith("adm_prod_wizbest_"))
async def wiz_best(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    value = 1 if callback.data.endswith("_1") else 0
    await state.update_data(is_best_value=value)
    data = await state.get_data()
    key = str(data.get("game_key") or "ff")
    _, game_name = GAME_KEYS.get(key, GAME_KEYS["ff"])
    label = format_product_label(str(data["raw_label"]), game_name)
    await state.update_data(final_label=label)
    await state.set_state(ProductWizard.waiting_confirm)
    await callback.message.answer(
        f"Предпросмотр:\n{label} — {fmt_price(float(data['price']))} смн\nСохранить?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Сохранить", callback_data="adm_prod_wizsave"),
                    InlineKeyboardButton(text="❌ Отмена", callback_data="adm_prod_wizcancel"),
                ]
            ]
        ),
    )


@router.callback_query(StateFilter(ProductWizard.waiting_confirm), F.data == "adm_prod_wizcancel")
async def wiz_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.answer("Отменено.")


@router.callback_query(StateFilter(ProductWizard.waiting_confirm), F.data == "adm_prod_wizsave")
async def wiz_save(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    key = str(data.get("game_key") or "ff")
    ff_sub = str(data.get("ff_subcategory") or "cis")
    gid = await _find_game_id_by_key(key)
    if not gid:
        await state.clear()
        await callback.message.answer("❌ Игра не найдена.")
        return
    sub = ff_sub if key == "ff" else "cis"
    if data["mode"] == "add":
        await db.insert_product(
            game_id=gid,
            label=data["final_label"],
            price_tjs=float(data["price"]),
            is_popular=int(data["is_popular"]),
            is_best_value=int(data["is_best_value"]),
            subcategory=sub,
        )
    else:
        await db.update_product(
            int(data["product_id"]),
            label=data["final_label"],
            price_tjs=float(data["price"]),
            is_popular=int(data["is_popular"]),
            is_best_value=int(data["is_best_value"]),
        )
    await state.clear()
    await callback.message.answer("✅ Сохранено")
    render_sub = ff_sub if key == "ff" else None
    await _render_products(callback, key, subcategory=render_sub)


@router.callback_query(F.data.startswith("adm_prod_delyes_"))
async def product_delete_yes(callback: CallbackQuery) -> None:
    await callback.answer()
    pid = int(callback.data.removeprefix("adm_prod_delyes_"))
    product = await db.get_product_by_id(pid)
    game_key = "ff"
    ff_sub: str | None = None
    if product:
        game = await db.get_game_by_id(int(product["game_id"]))
        if game:
            game_key = _game_key_from_db_name(str(game["name"]))
            if game_key == "ff":
                ff_sub = _ff_subcategory_from_product(product)
    await db.delete_product(pid)
    await callback.message.answer("🗑 Товар удалён.")
    await _render_products(callback, game_key, subcategory=ff_sub)


@router.callback_query(F.data.startswith("adm_prod_del_"))
async def product_delete_confirm(callback: CallbackQuery) -> None:
    await callback.answer()
    pid = int(callback.data.removeprefix("adm_prod_del_"))
    await callback.message.answer(
        "Удалить товар?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Да", callback_data=f"adm_prod_delyes_{pid}"),
                    InlineKeyboardButton(text="❌ Нет", callback_data="admin_products"),
                ]
            ]
        ),
    )


@router.callback_query(F.data.startswith("adm_prod_noop_"))
async def noop(callback: CallbackQuery) -> None:
    await callback.answer()
