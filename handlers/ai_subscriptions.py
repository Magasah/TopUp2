from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import config
from database import queries as db
from utils.assets import get_ai_photo
from utils.currency import format_payment_tjs_usd, get_usd_rate, usd_to_tjs
from utils.formatter import fmt_price_tjs
from utils.payment_flow import show_payment_methods, show_requisites
from utils.receipt_checker import append_receipt_note, check_receipt, register_receipt

router = Router()

AI_SERVICES: dict[str, dict] = {
    "chatgpt": {
        "name": "ChatGPT",
        "company": "OpenAI",
        "emoji": "🤖",
        "photo_key": "chat_gpt",
        "category": "text",
        "plans": [
            {"name": "Plus", "price_usd": 22, "desc": "GPT-4o, DALL-E, веб-поиск"},
            {"name": "Pro", "price_usd": 215, "desc": "o1 Pro, безлимит, API приоритет"},
            {"name": "Team", "price_usd": 33, "desc": "Для команд, расширенные лимиты"},
        ],
    },
    "claude": {
        "name": "Claude",
        "company": "Anthropic",
        "emoji": "🧠",
        "photo_key": "claude",
        "category": "text",
        "plans": [
            {"name": "Pro", "price_usd": 22, "desc": "Claude Sonnet 4, приоритет"},
            {"name": "Max 5x", "price_usd": 108, "desc": "В 5 раз больше сообщений"},
        ],
    },
    "gemini": {
        "name": "Gemini",
        "company": "Google",
        "emoji": "♊",
        "photo_key": "gemini",
        "category": "text",
        "plans": [
            {"name": "Advanced", "price_usd": 22, "desc": "Gemini 2.5 Pro, NotebookLM"},
            {"name": "Business", "price_usd": 26, "desc": "Для бизнеса, Workspace"},
        ],
    },
    "grok": {
        "name": "Grok",
        "company": "xAI",
        "emoji": "🐦",
        "photo_key": "grok",
        "category": "text",
        "plans": [
            {"name": "Premium", "price_usd": 10, "desc": "Grok 3, Aurora генерация"},
            {"name": "Premium+", "price_usd": 18, "desc": "DeepSearch, Think Mode"},
        ],
    },
    "cursor": {
        "name": "Cursor",
        "company": "Anysphere",
        "emoji": "🖱",
        "photo_key": "cursor",
        "category": "code",
        "plans": [
            {"name": "Pro", "price_usd": 22, "desc": "GPT-4o + Claude, 500 запросов"},
            {"name": "Business", "price_usd": 43, "desc": "Командный, приоритет"},
        ],
    },
    "copilot": {
        "name": "GitHub Copilot",
        "company": "GitHub",
        "emoji": "🐙",
        "photo_key": "github_copilot",
        "category": "code",
        "plans": [
            {"name": "Individual", "price_usd": 12, "desc": "VS Code, JetBrains, Neovim"},
            {"name": "Business", "price_usd": 21, "desc": "Для команд, управление"},
        ],
    },
    "midjourney": {
        "name": "Midjourney",
        "company": "Midjourney",
        "emoji": "🎨",
        "photo_key": "midjourney",
        "category": "image",
        "plans": [
            {"name": "Basic", "price_usd": 12, "desc": "200 изображений/мес"},
            {"name": "Standard", "price_usd": 33, "desc": "15ч GPU, неограниченные Relax"},
            {"name": "Pro", "price_usd": 65, "desc": "30ч GPU, Stealth режим"},
            {"name": "Mega", "price_usd": 130, "desc": "60ч GPU, максимум всего"},
        ],
    },
    "runway": {
        "name": "Runway",
        "company": "Runway",
        "emoji": "🎬",
        "photo_key": "runway",
        "category": "video",
        "plans": [
            {"name": "Standard", "price_usd": 17, "desc": "625 кредитов/мес"},
            {"name": "Pro", "price_usd": 38, "desc": "2250 кредитов, приоритет"},
            {"name": "Unlimited", "price_usd": 103, "desc": "Безлимит генераций"},
        ],
    },
    "kling": {
        "name": "Kling AI",
        "company": "Kuaishou",
        "emoji": "🎥",
        "photo_key": "kling",
        "category": "video",
        "plans": [
            {"name": "Pro", "price_usd": 12, "desc": "660 кредитов/мес"},
            {"name": "Premier", "price_usd": 40, "desc": "3000 кредитов/мес"},
        ],
    },
    "suno": {
        "name": "Suno",
        "company": "Suno",
        "emoji": "🎵",
        "photo_key": "suno",
        "category": "music",
        "plans": [
            {"name": "Pro", "price_usd": 12, "desc": "2500 кредитов, коммерция"},
            {"name": "Premier", "price_usd": 33, "desc": "10000 кредитов"},
        ],
    },
    "elevenlabs": {
        "name": "ElevenLabs",
        "company": "ElevenLabs",
        "emoji": "🔊",
        "photo_key": "elevenlabs",
        "category": "audio",
        "plans": [
            {"name": "Starter", "price_usd": 7, "desc": "30к символов/мес"},
            {"name": "Creator", "price_usd": 25, "desc": "100к символов, клонирование"},
            {"name": "Pro", "price_usd": 107, "desc": "500к символов, 44 голоса"},
        ],
    },
    "perplexity": {
        "name": "Perplexity",
        "company": "Perplexity AI",
        "emoji": "🔍",
        "photo_key": "perplexity",
        "category": "search",
        "plans": [
            {"name": "Pro", "price_usd": 22, "desc": "300+ запросов/день, GPT-4o/Claude"},
        ],
    },
}

CATEGORIES: dict[str, tuple[str, list[str]]] = {
    "text": ("💬 Чат и текст", ["chatgpt", "claude", "gemini", "grok", "perplexity"]),
    "code": ("💻 Разработка", ["cursor", "copilot"]),
    "image": ("🖼 Изображения", ["midjourney"]),
    "video": ("🎬 Видео", ["runway", "kling"]),
    "music": ("🎵 Музыка", ["suno"]),
    "audio": ("🔊 Голос и аудио", ["elevenlabs"]),
}

CATEGORY_DESC: dict[str, str] = {
    "text": "Чат-боты и текстовые нейросети",
    "code": "ИИ для программирования и разработки",
    "image": "Генерация и обработка изображений",
    "video": "Создание и монтаж видео с ИИ",
    "music": "Генерация музыки и треков",
    "audio": "Синтез речи и озвучка",
    "search": "Поиск и исследования с ИИ",
}

CAT_LOCALE_KEYS = {
    "text": "ai_cat_text",
    "code": "ai_cat_code",
    "image": "ai_cat_image",
    "video": "ai_cat_video",
    "music": "ai_cat_music",
    "audio": "ai_cat_audio",
}

PAYMENT_LABELS = {
    "pay_dc": "🏦 DC City",
    "pay_alif": "📱 Alif Mobi",
}


class AiSubStates(StatesGroup):
    waiting_confirm = State()
    waiting_payment_method = State()
    waiting_receipt = State()


def _categories_kb(t) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for cat_key, (title, _keys) in CATEGORIES.items():
        label = t(CAT_LOCALE_KEYS.get(cat_key, "ai_cat_text"))
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"ai_cat_{cat_key}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="other_games")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _services_kb(category: str) -> InlineKeyboardMarkup:
    _, keys = CATEGORIES[category]
    rows: list[list[InlineKeyboardButton]] = []
    for key in keys:
        svc = AI_SERVICES[key]
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{svc['emoji']} {svc['name']}",
                    callback_data=f"ai_service_{key}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="◀️ Назад к категориям", callback_data="ai_subs_start")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _plans_kb(service_key: str, rate: float) -> InlineKeyboardMarkup:
    svc = AI_SERVICES[service_key]
    plans = svc["plans"]
    rows: list[list[InlineKeyboardButton]] = []
    for idx, plan in enumerate(plans):
        usd = float(plan["price_usd"])
        tjs = round(usd * rate)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{plan['name']} — ${usd:g} (~{tjs} смн)",
                    callback_data=f"ai_plan_{service_key}_{idx}",
                )
            ]
        )
    cat = str(svc.get("category") or "text")
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"ai_cat_{cat}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _full_service_name(service_key: str, plan_name: str | None = None) -> str:
    svc = AI_SERVICES[service_key]
    base = f"{svc['name']} {plan_name}".strip() if plan_name else str(svc["name"])
    return base


@router.callback_query(F.data == "ai_subs_start")
async def ai_subs_start(callback: CallbackQuery, t) -> None:
    await callback.answer()
    rate = await get_usd_rate()
    text = t("ai_subs_menu", rate=f"{rate:g}")
    kb = _categories_kb(t)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("ai_cat_"))
async def ai_category(callback: CallbackQuery, t) -> None:
    await callback.answer()
    category = (callback.data or "").removeprefix("ai_cat_")
    if category not in CATEGORIES:
        return
    title, _ = CATEGORIES[category]
    rate = await get_usd_rate()
    text = (
        f"{title}\n"
        "─────────────────────────────\n"
        f"{CATEGORY_DESC.get(category, '')}\n"
        f"💵 Курс: 1 USD = {rate:g} смн\n"
        "─────────────────────────────\n"
        "Выберите сервис:"
    )
    kb = _services_kb(category)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("ai_service_"))
async def ai_service_card(callback: CallbackQuery) -> None:
    await callback.answer()
    service_key = (callback.data or "").removeprefix("ai_service_")
    svc = AI_SERVICES.get(service_key)
    if not svc:
        return
    rate = await get_usd_rate()
    cat = str(svc.get("category") or "text")
    desc = CATEGORY_DESC.get(cat, "")
    text = (
        f"{svc['emoji']} <b>{svc['name']}</b> — {svc['company']}\n"
        "─────────────────────────────\n"
        f"{desc}\n"
        f"💵 Курс: 1 USD = {rate:g} смн\n"
        "─────────────────────────────\n"
        "Выберите тариф:"
    )
    kb = _plans_kb(service_key, rate)
    photo = get_ai_photo(str(svc["photo_key"]))
    chat_id = callback.from_user.id
    if photo:
        await callback.bot.send_photo(
            chat_id,
            photo=photo,
            caption=text,
            parse_mode="HTML",
            reply_markup=kb,
        )
    else:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("ai_plan_"))
async def ai_plan_selected(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    raw = (callback.data or "").removeprefix("ai_plan_")
    service_key, idx_s = raw.rsplit("_", 1)
    try:
        plan_idx = int(idx_s)
    except ValueError:
        return
    svc = AI_SERVICES.get(service_key)
    if not svc or plan_idx < 0 or plan_idx >= len(svc["plans"]):
        return
    plan = svc["plans"][plan_idx]
    price_usd = float(plan["price_usd"])
    rate = await get_usd_rate()
    price_tjs = await usd_to_tjs(price_usd)
    service_name = _full_service_name(service_key, str(plan["name"]))
    await state.update_data(
        service_key=service_key,
        plan_index=plan_idx,
        plan_name=str(plan["name"]),
        plan_desc=str(plan.get("desc") or ""),
        service_name=service_name,
        service_label=str(svc["name"]),
        service_emoji=str(svc["emoji"]),
        price_usd=price_usd,
        price_tjs=price_tjs,
        usd_rate=rate,
        period="1 месяц",
    )
    await state.set_state(AiSubStates.waiting_confirm)
    user = callback.from_user
    text = (
        "📋 ВАША ЗАЯВКА\n"
        "─────────────────────────────\n"
        f"👤 Покупатель: {user.full_name}\n"
        f"📱 Telegram: @{user.username or 'нет'}\n"
        f"🤖 Сервис: {svc['emoji']} {svc['name']}\n"
        f"📦 Тариф: {plan['name']}\n"
        f"📋 Описание: {plan.get('desc', '')}\n"
        f"💵 Сумма: {price_usd:g} USD\n"
        f"💰 К оплате: {fmt_price_tjs(price_tjs)}\n"
        f"📈 Курс: 1 USD = {rate:g} смн\n"
        "⏱ Период: 1 месяц\n"
        "─────────────────────────────\n"
        "Всё верно?"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Оплатить", callback_data="ai_confirm_pay")],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=f"ai_service_{service_key}",
                )
            ],
        ]
    )
    await callback.message.answer(text, reply_markup=kb)


@router.callback_query(StateFilter(AiSubStates.waiting_confirm), F.data == "ai_confirm_pay")
async def ai_confirm_pay(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    await show_payment_methods(callback.from_user.id, f"{float(data['price_tjs']):g}", "смн")
    await state.set_state(AiSubStates.waiting_payment_method)


@router.callback_query(StateFilter(AiSubStates.waiting_receipt), F.data == "ai_confirm_pay")
async def ai_back_to_payment_methods(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    await show_payment_methods(callback.from_user.id, f"{float(data['price_tjs']):g}", "смн")
    await state.set_state(AiSubStates.waiting_payment_method)


@router.callback_query(
    StateFilter(AiSubStates.waiting_payment_method),
    F.data.in_(["pay_dc", "pay_alif"]),
)
async def ai_payment_method(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    await state.update_data(payment_method=callback.data)
    await show_requisites(
        callback.from_user.id,
        str(callback.data),
        f"{float(data['price_tjs']):g}",
        "смн",
    )
    await callback.message.answer(
        format_payment_tjs_usd(
            float(data["price_tjs"]),
            float(data["price_usd"]),
            float(data["usd_rate"]),
        )
        + "\n\n📸 Отправьте фото чека.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="ai_confirm_pay")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment")],
            ]
        ),
    )
    await state.set_state(AiSubStates.waiting_receipt)


@router.message(StateFilter(AiSubStates.waiting_receipt), F.photo)
async def ai_receipt(message: Message, state: FSMContext, t) -> None:
    is_dup, dup_text = await check_receipt(message, "ai_sub", t)
    if is_dup:
        await message.answer(dup_text, parse_mode="HTML")
        return

    data = await state.get_data()
    photo = message.photo[-1]
    photo_id = photo.file_id
    service_key = str(data["service_key"])
    svc = AI_SERVICES[service_key]
    order_id = await db.create_ai_sub_order(
        user_tg_id=message.from_user.id,
        username=message.from_user.username or "",
        service_name=str(data["service_name"]),
        service_key=service_key,
        plan_name=str(data["plan_name"]),
        price_usd=float(data["price_usd"]),
        price_tjs=float(data["price_tjs"]),
        usd_rate=float(data["usd_rate"]),
        payment_method=str(data["payment_method"]),
        receipt_file_id=photo_id,
        period=str(data.get("period") or "1 месяц"),
    )
    await register_receipt(
        photo.file_unique_id, photo_id, message.from_user.id, "ai_sub", order_id
    )
    await state.clear()
    await message.answer(
        t(
            "ai_sub_accepted",
            id=order_id,
            service=str(data["service_label"]),
            plan=str(data["plan_name"]),
        )
    )
    pay_label = PAYMENT_LABELS.get(str(data["payment_method"]), str(data["payment_method"]))
    admin_text = (
        f"🤖 ИИ ПОДПИСКА #{order_id}\n"
        "─────────────────────────────\n"
        f"👤 {message.from_user.full_name} | @{message.from_user.username or 'нет'}\n"
        f"{svc['emoji']} Сервис: {data['service_name']}\n"
        f"📦 Тариф: {data['plan_name']}\n"
        f"💵 {float(data['price_usd']):g} USD → {float(data['price_tjs']):g} смн\n"
        f"📈 Курс: {float(data['usd_rate']):g}\n"
        f"💳 Оплата: {pay_label}"
    )
    admin_text = append_receipt_note(admin_text, t)
    admin_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Принять",
                    callback_data=f"order_accept_ai_sub_{order_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"order_reject_ai_sub_{order_id}",
                ),
                InlineKeyboardButton(
                    text="💬 Написать",
                    url=f"tg://user?id={message.from_user.id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=f"order_delete_ai_sub_{order_id}",
                )
            ],
        ]
    )
    for admin_id in config.admin_ids_list:
        try:
            await message.bot.send_photo(admin_id, photo=photo_id, caption=admin_text)
            await message.bot.send_message(admin_id, "Управление заказом:", reply_markup=admin_kb)
        except Exception:
            pass


@router.message(StateFilter(AiSubStates.waiting_receipt), ~F.photo)
async def ai_wrong_receipt(message: Message) -> None:
    await message.answer("❌ Отправьте именно фото чека.")

# ✅ ГОТОВО: handlers/ai_subscriptions.py
