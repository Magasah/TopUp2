from datetime import datetime
from typing import Any, Optional


def fmt_price(amount: float | int | str | None, currency: str = "смн") -> str:
    """Форматирование цены для отображения."""
    try:
        value = float(amount or 0)
    except (TypeError, ValueError):
        value = 0.0

    if currency == "смн":
        if value == int(value):
            return f"{int(value)} смн"
        return f"{value:.1f} смн"
    if currency == "сомони":
        if value == int(value):
            return f"{int(value)} сомони"
        return f"{value:.1f} сомони"
    if currency == "TJS":
        if value == int(value):
            return f"{int(value)} TJS"
        return f"{value:.1f} TJS"
    if currency == "₽":
        if value == int(value):
            return f"{int(value)} ₽"
        return f"{value:.1f} ₽"
    if currency == "$":
        return f"${value:.2f}"
    if value == int(value):
        return f"{int(value)} {currency}"
    return f"{value:.1f} {currency}"


def fmt_price_tjs(amount: float | int | str | None) -> str:
    """Специально для таджикских сомони (смн)."""
    return fmt_price(amount, "смн")


def format_product_label(raw: str, game_name: str) -> str:
    s = raw.strip()
    if "standoff" in (game_name or "").lower():
        return s
    if any(ch in s for ch in ("💎", "🎮", "UC", "алмаз")):
        return s
    if s.isdigit():
        if "pubg" in game_name.lower() or "uc" in game_name.lower():
            return f"🎮 {s} UC"
        return f"💎 {s} алмазов"
    return s


def format_order_status(status: str) -> str:
    return {
        "pending": "⏳ ожидание",
        "accepted": "✅ принят",
        "rejected": "❌ отклонён",
    }.get(status, status)


def format_dt(value: Optional[str]) -> str:
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return value


def payment_label(method: str) -> str:
    return {
        "dc": "DC City",
        "pay_dc": "DC City",
        "alif": "Alif Mobi",
        "pay_alif": "Alif Mobi",
        "card": "MasterCard",
        "pay_card": "MasterCard",
        "milli": "Korti Milli",
        "pay_milli": "Korti Milli",
    }.get(method, method or "—")


def escape_minimal(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def order_to_card(o: dict[str, Any], t) -> str:
    user = o.get("username") or "—"
    return t(
        "order_card",
        oid=o.get("id"),
        user=user,
        game=escape_minimal(str(o.get("game_name") or "")),
        product=escape_minimal(str(o.get("product_label") or "")),
        price=fmt_price_tjs(o.get("price_tjs")),
        gid=o.get("game_account_id") or "",
        pay=payment_label(str(o.get("payment_method") or "")),
        status=format_order_status(str(o.get("status") or "")),
        created=format_dt(o.get("created_at")),
    )

# ✅ ГОТОВО: utils/formatter.py
