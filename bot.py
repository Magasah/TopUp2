import asyncio
import atexit
import logging
import os
import subprocess
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    BotCommandScopeDefault,
    MenuButtonCommands,
)

from config import config
from database.db import init_db
from handlers import (
    black_russia,
    ff_settings,
    free_settings,
    games,
    gifts_webapp,
    order,
    payment,
    referral,
    settings,
    standoff,
    start,
    steam,
    ai_subscriptions,
    telegram_services,
    tournament,
)
from handlers.admin import (
    admins_mgr,
    all_orders,
    br_orders,
    broadcast,
    games_mgr,
    maintenance,
    panel,
    products_panel,
    required_subscriptions,
    settings_orders,
    stats,
    wallets,
)
from utils.currency import fetch_usd_rate
from middlewares.admin_only import AdminOnlyMiddleware
from middlewares.anti_spam import AntiSpamMiddleware
from middlewares.i18n import I18nMiddleware
from middlewares.ban_check import BanCheckMiddleware
from middlewares.maintenance import MaintenanceMiddleware
from middlewares.state_guard import StateGuardMiddleware
from middlewares.subscription import SubscriptionMiddleware
from middlewares.user_lang import UserLangMiddleware

logging.basicConfig(level=logging.INFO)

_LOCK_PATH = Path(__file__).resolve().parent / ".bot.lock"


def _is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
            check=False,
        )
        out = (result.stdout or "").lower()
        return str(pid) in out and ".exe" in out
    except Exception:
        return False


def _acquire_single_instance_lock() -> None:
    if _LOCK_PATH.exists():
        try:
            raw = _LOCK_PATH.read_text(encoding="utf-8").strip()
            old_pid = int(raw) if raw else 0
        except Exception:
            old_pid = 0
        if old_pid and _is_pid_running(old_pid):
            logging.error("Обнаружен уже запущенный bot.py (pid=%s). Второй запуск остановлен.", old_pid)
            sys.exit(1)
        try:
            _LOCK_PATH.unlink()
        except Exception:
            pass
    _LOCK_PATH.write_text(str(os.getpid()), encoding="utf-8")

    def _cleanup() -> None:
        try:
            if _LOCK_PATH.exists():
                _LOCK_PATH.unlink()
        except Exception:
            pass

    atexit.register(_cleanup)


async def schedule_rate_update() -> None:
    while True:
        await asyncio.sleep(24 * 3600)
        rate = await fetch_usd_rate()
        if rate is not None:
            from database.queries import set_setting
            from datetime import datetime

            await set_setting("usd_rate", str(rate))
            await set_setting("usd_rate_updated", datetime.now().isoformat())


async def on_startup() -> None:
    await init_db()
    from utils.admins import refresh_admins_cache

    await refresh_admins_cache()
    rate = await fetch_usd_rate()
    if rate is not None:
        from database.queries import set_setting
        from datetime import datetime

        await set_setting("usd_rate", str(rate))
        await set_setting("usd_rate_updated", datetime.now().isoformat())
    asyncio.create_task(schedule_rate_update())


async def set_bot_commands(bot: Bot) -> None:
    """Подсказки команд в Telegram.

    Всем пользователям — только /start. Администраторам из списка (ENV + БД)
    дополнительно выдаётся /admin через персональный scope BotCommandScopeChat.
    """
    from utils.admins import get_admin_ids

    user_cmds = [
        BotCommand(command="start", description="Перезапустить бота"),
    ]
    admin_cmds = [
        BotCommand(command="start", description="Перезапустить бота"),
        BotCommand(command="admin", description="Панель администратора"),
    ]
    try:
        await bot.set_my_commands(user_cmds, scope=BotCommandScopeDefault())
        await bot.set_my_commands(user_cmds, scope=BotCommandScopeAllPrivateChats())
        await bot.set_my_commands([], scope=BotCommandScopeAllGroupChats())
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        for admin_id in get_admin_ids():
            try:
                await bot.set_my_commands(
                    admin_cmds,
                    scope=BotCommandScopeChat(chat_id=admin_id),
                )
            except Exception as exc:
                logging.warning("set_my_commands для chat_id=%s: %s", admin_id, exc)
    except Exception as exc:
        logging.warning("Не удалось обновить меню команд: %s", exc)


async def main() -> None:
    _acquire_single_instance_lock()
    await on_startup()

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    _maint = MaintenanceMiddleware()
    dp.message.middleware(_maint)
    dp.callback_query.middleware(_maint)

    _ban = BanCheckMiddleware()
    dp.message.middleware(_ban)
    dp.callback_query.middleware(_ban)

    for mw in (
        StateGuardMiddleware(),
        UserLangMiddleware(),
        I18nMiddleware(),
        AntiSpamMiddleware(),
        SubscriptionMiddleware(),
    ):
        dp.message.middleware(mw)
        dp.callback_query.middleware(mw)

    admin = Router(name="admin")
    admin.message.middleware(AdminOnlyMiddleware())
    admin.callback_query.middleware(AdminOnlyMiddleware())
    admin.include_router(panel.router)
    admin.include_router(stats.router)
    admin.include_router(all_orders.router)
    admin.include_router(products_panel.router)
    admin.include_router(games_mgr.router)
    admin.include_router(broadcast.router)
    admin.include_router(maintenance.router)
    admin.include_router(required_subscriptions.router)
    admin.include_router(settings_orders.router)
    admin.include_router(br_orders.router)
    admin.include_router(wallets.router)
    admin.include_router(admins_mgr.router)

    dp.include_router(start.router)
    dp.include_router(settings.router)
    dp.include_router(referral.router)
    dp.include_router(games.router)
    dp.include_router(free_settings.router)
    dp.include_router(ff_settings.router)
    dp.include_router(black_russia.router)
    dp.include_router(standoff.router)
    dp.include_router(tournament.router)
    dp.include_router(steam.router)
    dp.include_router(ai_subscriptions.router)
    dp.include_router(telegram_services.router)
    dp.include_router(gifts_webapp.router)
    dp.include_router(order.router)
    dp.include_router(payment.router)
    dp.include_router(admin)

    await set_bot_commands(bot)

    await bot.delete_webhook(drop_pending_updates=True)

    logging.info("Бот запущен")
    await dp.start_polling(bot, handle_as_tasks=False)


if __name__ == "__main__":
    asyncio.run(main())

# ✅ ГОТОВО: bot.py
