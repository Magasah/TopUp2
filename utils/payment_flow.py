from typing import Any

from config import config
from utils import tg_api


def _payment_kb() -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [{"text": "🏦 DC City", "callback_data": "pay_dc", "style": "primary"}],
            [{"text": "📱 Alif Mobi", "callback_data": "pay_alif", "style": "success"}],
            [{"text": "❌ Отменить оплату", "callback_data": "cancel_payment", "style": "danger"}],
        ]
    }


async def show_payment_methods(chat_id: int, amount: str, currency: str = "смн") -> None:
    text = (
        "💳 Выберите способ оплаты\n"
        "───────────────────────\n"
        f"💰 Сумма к оплате: {amount} {currency}"
    )
    await tg_api.send_message(chat_id, text, _payment_kb())


async def _wallet(setting_key: str, env_value: str, hardcoded: str) -> str:
    """Номер кошелька: приоритет у значения из БД (админ-панель «Кошельки»)."""
    from database.queries import get_setting

    db_value = await get_setting(setting_key)
    return (db_value or env_value or hardcoded).strip()


async def show_requisites(chat_id: int, method: str, amount: str, currency: str = "смн") -> None:
    dc_num = await _wallet("wallet_dc", (config.DC_CITY_NUMBER or "").strip(), "+992 888788181")
    alif_num = await _wallet("wallet_alif", (config.ALIF_NUMBER or "").strip(), "+992 888788181")
    methods = {
        "pay_dc": {"name": "🏦 DC City", "number": dc_num, "icon": "🏦", "copy": "📋 Скопировать DC City"},
        "pay_alif": {"name": "📱 Alif Mobi", "number": alif_num, "icon": "📱", "copy": "📋 Скопировать Alif Mobi"},
    }
    m = methods.get(method)
    if not m:
        return
    text = (
        f"{m['icon']} {m['name']}\n"
        "───────────────────────\n"
        f"📋 Номер: <code>{m['number']}</code>\n"
        f"💰 Сумма: {amount} {currency}\n"
        "───────────────────────\n"
        "После оплаты отправьте скриншот чека 📸"
    )
    kb: dict[str, Any] = {
        "inline_keyboard": [
            [{"text": m["copy"], "copy_text": {"text": str(m["number"])}}],
            [{"text": "❌ Отменить оплату", "callback_data": "cancel_payment", "style": "danger"}],
        ]
    }
    await tg_api.send_message(chat_id, text, kb)


# ✅ ГОТОВО: utils/payment_flow.py
