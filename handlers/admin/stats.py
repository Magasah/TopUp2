from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import config
from database.queries import get_period_stats, get_stats
from utils.formatter import fmt_price

router = Router()

_PERIOD_LABELS = [
    ("7d", "За 7 дней"),
    ("30d", "За 30 дней"),
    ("130d", "За 130 дней"),
    ("year", "За год"),
    ("all", "За всё время"),
]


def _period_block(periods: dict) -> str:
    lines = ["📅 <b>По периодам (пользователи / заказы)</b>"]
    for key, label in _PERIOD_LABELS:
        row = periods.get(key, {})
        lines.append(
            f"· {label}: 👥 {row.get('users', 0)} / 📦 {row.get('orders', 0)}"
        )
    return "\n".join(lines)


def _stats_text(s: dict, t) -> str:
    return (
        f"{t('stats_title')}\n"
        f"{t('stats_sep')}\n"
        f"<b>{t('stats_block_audience')}</b>\n"
        f"· {t('stats_users_unique', n=s.get('users', 0))}\n"
        f"· {t('stats_starts_total', n=s.get('start_commands', 0))}\n"
        f"· {t('stats_users_new_24h', n=s.get('users_24h', 0))}\n"
        f"· {t('stats_users_new_7d', n=s.get('users_7d', 0))}\n"
        f"· {t('stats_active_24h', n=s.get('active_24h', 0))}\n"
        f"· {t('stats_referrals', n=s.get('referrals_total', 0))}\n"
        f"{t('stats_sep')}\n"
        f"<b>{t('stats_block_orders')}</b>\n"
        f"· {t('stats_orders_all', n=s.get('orders_all', 0))}\n"
        f"· {t('stats_orders_pending', n=s.get('pending_all', 0))}\n"
        f"· {t('stats_orders_done', n=s.get('accepted_all', 0))}\n"
        f"· {t('stats_orders_reject', n=s.get('rejected_all', 0))}\n"
        f"· {t('stats_tournaments_open', n=s.get('tournaments_open', 0))}\n"
        f"{t('stats_sep')}\n"
        f"<b>{t('stats_block_money')}</b>\n"
        f"· {t('stats_revenue_all', v=fmt_price(s.get('revenue_all_tjs', 0)))}\n"
        f"· {t('stats_revenue_ff_pubg', v=fmt_price(s.get('revenue_tjs', 0)))}\n"
        f"· {t('stats_note_br')}\n"
        f"{t('stats_sep')}\n"
        f"<b>{t('stats_block_by_service')}</b>\n"
        f"· FF/PUBG заказов: {s.get('orders_total', 0)}\n"
        f"· Black Russia: {s.get('br_orders', 0)}\n"
        f"· Steam: {s.get('steam_orders', 0)}\n"
        f"· Standoff 2: {s.get('standoff_orders', 0)}\n"
        f"· Настройки FF: {s.get('ff_settings_orders', 0)}\n"
        f"· VIP панели: {s.get('vip_orders', 0)}\n"
        f"· Telegram (Stars/Premium): {s.get('tg_service_orders', 0)}"
    )


async def _send_stats_message(message: Message, t) -> None:
    s = await get_stats()
    periods = await get_period_stats()
    text = _stats_text(s, t) + "\n" + t("stats_sep") + "\n" + _period_block(periods)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("back"), callback_data="adm_back_panel")]
        ]
    )
    await message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)


@router.message(Command("stats"))
async def cmd_stats(message: Message, t) -> None:
    await _send_stats_message(message, t)


@router.callback_query(F.data == "adm_stats")
async def show_stats(callback: CallbackQuery, t) -> None:
    await callback.answer()
    s = await get_stats()
    periods = await get_period_stats()
    text = _stats_text(s, t) + "\n" + t("stats_sep") + "\n" + _period_block(periods)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("back"), callback_data="adm_back_panel")]
        ]
    )
    await callback.message.edit_text(
        text,
        reply_markup=kb,
        parse_mode=ParseMode.HTML,
    )
