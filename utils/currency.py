from datetime import datetime, timedelta

import aiohttp

from database.queries import get_setting, set_setting


async def fetch_usd_rate() -> float | None:
    """Попробовать несколько источников курса USD -> TJS."""
    sources = [
        "https://api.exchangerate-api.com/v4/latest/USD",
        "https://open.er-api.com/v6/latest/USD",
        "https://api.frankfurter.app/latest?from=USD&to=TJS",
    ]
    for url in sources:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    data = await resp.json()
                    rates = data.get("rates", {})
                    if "TJS" in rates:
                        return float(rates["TJS"])
        except Exception:
            continue
    return None


async def get_usd_rate() -> float:
    """Получить курс USD -> TJS с кэшем 24 часа."""
    cached = await get_setting("usd_rate")
    cached_time = await get_setting("usd_rate_updated")
    if cached and cached_time:
        try:
            updated = datetime.fromisoformat(cached_time)
            if datetime.now() - updated < timedelta(hours=24):
                return float(cached)
        except Exception:
            pass

    rate = await fetch_usd_rate()
    if rate is not None:
        await set_setting("usd_rate", str(rate))
        await set_setting("usd_rate_updated", datetime.now().isoformat())
        return rate
    return float(cached or 11.5)


async def get_live_usd_rate() -> float:
    """Получить максимально свежий курс, с fallback на кэш."""
    rate = await fetch_usd_rate()
    if rate is not None:
        await set_setting("usd_rate", str(rate))
        await set_setting("usd_rate_updated", datetime.now().isoformat())
        return rate
    return await get_usd_rate()


async def usd_to_tjs(usd: float) -> float:
    rate = await get_usd_rate()
    return round(usd * rate, 1)


async def usd_to_tjs_with_markup(usd: float, markup_percent: float = 10.0) -> tuple[float, float]:
    """Конвертация USD -> TJS по свежему курсу + наценка."""
    rate = await get_live_usd_rate()
    total_rate = rate * (1.0 + markup_percent / 100.0)
    return round(usd * total_rate, 1), round(total_rate, 4)


async def get_rate_info() -> str:
    """Для отображения пользователю: 1 USD = 11.5 смн (обновлено 2ч назад)."""
    rate = await get_setting("usd_rate") or "11.5"
    updated = await get_setting("usd_rate_updated")
    if updated:
        try:
            delta = datetime.now() - datetime.fromisoformat(updated)
            hours = int(delta.total_seconds() / 3600)
            time_str = f"{hours}ч назад" if hours > 0 else "только что"
        except Exception:
            time_str = "неизвестно"
    else:
        time_str = "неизвестно"
    return f"1 USD = {rate} смн (обновлено {time_str})"


def format_payment_tjs_usd(amount_tjs: float, amount_usd: float, rate: float) -> str:
    """Строка «к оплате в смн» с эквивалентом в USD для Steam / ИИ."""
    from utils.formatter import fmt_price_tjs

    tjs_s = fmt_price_tjs(amount_tjs)
    return (
        f"💰 К оплате: {tjs_s}\n"
        f"💵 Эквивалент: {amount_usd:g} USD (курс: 1$ = {rate:g} смн)"
    )
