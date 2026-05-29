import time
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

import aiosqlite
from aiogram.types import User as TgUser

from database.db import get_db_path


def _row_to_dict(row: aiosqlite.Row) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}


async def record_bot_start_command() -> None:
    """Увеличить счётчик нажатий /start (все вызовы, не только новые юзеры)."""
    now = datetime.utcnow().isoformat(timespec="seconds")
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            """INSERT INTO bot_metrics(key, value, updated_at) VALUES('start_commands', 1, ?)
               ON CONFLICT(key) DO UPDATE SET
                 value = value + 1,
                 updated_at = excluded.updated_at""",
            (now,),
        )
        await db.commit()


async def upsert_user(tg_user: TgUser, language: Optional[str] = None) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    async with aiosqlite.connect(get_db_path()) as db:
        if language:
            await db.execute(
                """INSERT INTO users(tg_id, username, first_name, language, last_active)
                   VALUES(?,?,?,?,?)
                   ON CONFLICT(tg_id) DO UPDATE SET
                     username=excluded.username,
                     first_name=excluded.first_name,
                     language=excluded.language,
                     last_active=excluded.last_active""",
                (
                    tg_user.id,
                    tg_user.username,
                    tg_user.first_name,
                    language,
                    now,
                ),
            )
        else:
            await db.execute(
                """INSERT INTO users(tg_id, username, first_name, language, last_active)
                   VALUES(?,?,?, 'tj', ?)
                   ON CONFLICT(tg_id) DO UPDATE SET
                     username=excluded.username,
                     first_name=excluded.first_name,
                     last_active=excluded.last_active""",
                (
                    tg_user.id,
                    tg_user.username,
                    tg_user.first_name,
                    now,
                ),
            )
        await db.commit()


async def set_user_language(tg_id: int, language: str) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            """INSERT INTO users(tg_id, username, first_name, language, last_active)
               VALUES(?, '', '', ?, ?)
               ON CONFLICT(tg_id) DO UPDATE SET
                 language=excluded.language,
                 last_active=excluded.last_active""",
            (tg_id, language, datetime.utcnow().isoformat(timespec="seconds")),
        )
        await db.commit()


async def get_user_language(tg_id: int) -> str:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT language FROM users WHERE tg_id = ?",
            (tg_id,),
        )
        row = await cur.fetchone()
        if row and row["language"]:
            return str(row["language"])
    return "tj"


async def touch_user(tg_id: int) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "UPDATE users SET last_active = ? WHERE tg_id = ?",
            (now, tg_id),
        )
        await db.commit()


async def get_all_games(active_only: bool = True) -> List[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        q = "SELECT * FROM games"
        if active_only:
            q += " WHERE is_active = 1"
        q += " ORDER BY id"
        cur = await db.execute(q)
        rows = await cur.fetchall()
        return [_row_to_dict(r) for r in rows]


async def get_game_by_id(game_id: int) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM games WHERE id = ?", (game_id,))
        row = await cur.fetchone()
        return _row_to_dict(row) if row else None


async def get_game_by_name(game_name: str) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM games WHERE LOWER(name) = LOWER(?) LIMIT 1",
            (game_name,),
        )
        row = await cur.fetchone()
        return _row_to_dict(row) if row else None


def _subcategory_sql_clause(subcategory: str | None) -> tuple[str, list[Any]]:
    """Фильтр региона доната Free Fire: cis (по умолчанию) или indonesia."""
    if subcategory is None:
        return "", []
    sub = (subcategory or "").strip().lower()
    if sub == "indonesia":
        return " AND subcategory = 'indonesia'", []
    # СНГ: старые записи без subcategory считаются СНГ
    return " AND (subcategory IS NULL OR subcategory = '' OR subcategory = 'cis')", []


async def get_products_by_game(
    game_id: int,
    active_only: bool = True,
    subcategory: str | None = None,
) -> List[dict[str, Any]]:
    sub_sql, sub_params = _subcategory_sql_clause(subcategory)
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        if active_only:
            cur = await db.execute(
                f"""SELECT * FROM products
                   WHERE game_id = ? AND is_active = 1{sub_sql}
                   ORDER BY sort_order ASC, id ASC""",
                (game_id, *sub_params),
            )
        else:
            cur = await db.execute(
                f"""SELECT * FROM products
                   WHERE game_id = ?{sub_sql}
                   ORDER BY sort_order ASC, id ASC""",
                (game_id, *sub_params),
            )
        rows = await cur.fetchall()
        return [_row_to_dict(r) for r in rows]


async def get_product_by_id(product_id: int) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = await cur.fetchone()
        return _row_to_dict(row) if row else None


async def create_order(
    user_tg_id: int,
    username: Optional[str],
    game_name: str,
    product_label: str,
    price_tjs: float,
    game_account_id: str,
    payment_method: str,
    receipt_file_id: str,
    status: str = "pending",
) -> int:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            """INSERT INTO orders(
                user_tg_id, username, game_name, product_label, price_tjs,
                game_account_id, payment_method, receipt_file_id, status
            ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                user_tg_id,
                username,
                game_name,
                product_label,
                price_tjs,
                game_account_id,
                payment_method,
                receipt_file_id,
                status,
            ),
        )
        await db.commit()
        return int(cur.lastrowid)


async def get_order_by_id(order_id: int) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = await cur.fetchone()
        return _row_to_dict(row) if row else None


async def get_order(order_id: int) -> Optional[dict[str, Any]]:
    return await get_order_by_id(order_id)


async def get_last_completed_order(user_tg_id: int) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT o.* FROM orders o
               WHERE o.user_tg_id = ? AND o.status = 'accepted'
               AND NOT EXISTS (SELECT 1 FROM reviews r WHERE r.order_id = o.id)
               ORDER BY COALESCE(o.completed_at, o.created_at) DESC, o.id DESC
               LIMIT 1""",
            (user_tg_id,),
        )
        row = await cur.fetchone()
        return _row_to_dict(row) if row else None


async def find_imported_review_order(user_tg_id: int, marker: str) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT * FROM orders
               WHERE user_tg_id = ?
                 AND product_label = ?
                 AND status = 'accepted'
                 AND NOT EXISTS (SELECT 1 FROM reviews r WHERE r.order_id = orders.id)
               ORDER BY COALESCE(completed_at, created_at) DESC, id DESC
               LIMIT 1""",
            (user_tg_id, marker),
        )
        row = await cur.fetchone()
        return _row_to_dict(row) if row else None


async def create_accepted_order_for_review(
    user_tg_id: int,
    username: Optional[str],
    game_name: str,
    product_label: str,
    price_tjs: float,
    game_account_id: str,
    payment_method: str,
    receipt_file_id: str,
) -> int:
    now = datetime.utcnow().isoformat(timespec="seconds")
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            """INSERT INTO orders(
                user_tg_id, username, game_name, product_label, price_tjs,
                game_account_id, payment_method, receipt_file_id, status, completed_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                user_tg_id,
                username,
                game_name,
                product_label,
                price_tjs,
                game_account_id,
                payment_method,
                receipt_file_id,
                "accepted",
                now,
            ),
        )
        await db.commit()
        return int(cur.lastrowid)


async def get_last_completed_settings_order(user_tg_id: int) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT * FROM settings_orders
               WHERE user_tg_id = ? AND status = 'accepted'
               ORDER BY COALESCE(completed_at, created_at) DESC, id DESC
               LIMIT 1""",
            (user_tg_id,),
        )
        row = await cur.fetchone()
        return _row_to_dict(row) if row else None


async def get_last_completed_br_order(user_tg_id: int) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT * FROM br_orders
               WHERE user_tg_id = ? AND status = 'accepted'
               ORDER BY COALESCE(completed_at, created_at) DESC, id DESC
               LIMIT 1""",
            (user_tg_id,),
        )
        row = await cur.fetchone()
        return _row_to_dict(row) if row else None


async def delete_order(order_id: int) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("DELETE FROM reviews WHERE order_id = ?", (order_id,))
        await db.execute("DELETE FROM orders WHERE id = ?", (order_id,))
        await db.commit()


async def update_order_status(
    order_id: int,
    status: str,
    completed: bool = False,
) -> None:
    completed_at = datetime.utcnow().isoformat(timespec="seconds") if completed else None
    async with aiosqlite.connect(get_db_path()) as db:
        if completed_at:
            await db.execute(
                "UPDATE orders SET status = ?, completed_at = ? WHERE id = ?",
                (status, completed_at, order_id),
            )
        else:
            await db.execute(
                "UPDATE orders SET status = ? WHERE id = ?",
                (status, order_id),
            )
        await db.commit()


async def get_orders_by_status(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cur = await db.execute(
                """SELECT * FROM orders WHERE status = ?
                   ORDER BY created_at DESC LIMIT ? OFFSET ?""",
                (status, limit, offset),
            )
        else:
            cur = await db.execute(
                """SELECT * FROM orders
                   ORDER BY created_at DESC LIMIT ? OFFSET ?""",
                (limit, offset),
            )
        rows = await cur.fetchall()
        return [_row_to_dict(r) for r in rows]


async def count_all_orders() -> int:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute("SELECT COUNT(*) FROM orders")
        row = await cur.fetchone()
        return int(row[0]) if row else 0


async def count_orders_by_status(status: str) -> int:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            "SELECT COUNT(*) AS c FROM orders WHERE status = ?",
            (status,),
        )
        row = await cur.fetchone()
        return int(row[0]) if row else 0


async def count_recent_orders_for_user(user_tg_id: int, hours: int = 1) -> int:
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat(timespec="seconds")
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            """SELECT COUNT(*) AS c FROM orders
               WHERE user_tg_id = ? AND created_at >= ?""",
            (user_tg_id, since),
        )
        row = await cur.fetchone()
        return int(row[0]) if row else 0


async def create_review(
    order_id: int,
    user_tg_id: int,
    text: str,
    status: str = "pending",
) -> int:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            """INSERT INTO reviews(order_id, user_tg_id, text, status)
               VALUES(?,?,?,?)""",
            (order_id, user_tg_id, text, status),
        )
        await db.commit()
        return int(cur.lastrowid)


async def get_review_by_id(review_id: int) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM reviews WHERE id = ?", (review_id,))
        row = await cur.fetchone()
        return _row_to_dict(row) if row else None


async def get_review(review_id: int) -> Optional[dict[str, Any]]:
    return await get_review_by_id(review_id)


async def get_pending_reviews() -> List[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM reviews WHERE status = 'pending' ORDER BY id DESC"
        )
        rows = await cur.fetchall()
        return [_row_to_dict(r) for r in rows]


async def update_review_text(review_id: int, text: str) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "UPDATE reviews SET text = ? WHERE id = ?",
            (text, review_id),
        )
        await db.commit()


async def update_review_status(
    review_id: int,
    status: str,
    channel_msg_id: Optional[int] = None,
) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        if channel_msg_id is not None:
            await db.execute(
                """UPDATE reviews SET status = ?, channel_msg_id = ?
                   WHERE id = ?""",
                (status, channel_msg_id, review_id),
            )
        else:
            await db.execute(
                "UPDATE reviews SET status = ? WHERE id = ?",
                (status, review_id),
            )
        await db.commit()


async def get_stats() -> dict[str, Any]:
    async with aiosqlite.connect(get_db_path()) as db:
        users = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        orders_total = (await (await db.execute("SELECT COUNT(*) FROM orders")).fetchone())[
            0
        ]
        pending = (
            await (
                await db.execute(
                    "SELECT COUNT(*) FROM orders WHERE status = 'pending'"
                )
            ).fetchone()
        )[0]
        accepted = (
            await (
                await db.execute(
                    "SELECT COUNT(*) FROM orders WHERE status = 'accepted'"
                )
            ).fetchone()
        )[0]
        rejected = (
            await (
                await db.execute(
                    "SELECT COUNT(*) FROM orders WHERE status = 'rejected'"
                )
            ).fetchone()
        )[0]
        revenue_row = await (
            await db.execute(
                """SELECT COALESCE(SUM(price_tjs),0) FROM orders
                   WHERE status = 'accepted'"""
            )
        ).fetchone()
        revenue = float(revenue_row[0]) if revenue_row else 0.0
        ff_settings_orders = (
            await (await db.execute("SELECT COUNT(*) FROM settings_orders")).fetchone()
        )[0]
        br_orders = (await (await db.execute("SELECT COUNT(*) FROM br_orders")).fetchone())[0]
        vip_orders = (
            await (
                await db.execute(
                    "SELECT COUNT(*) FROM settings_orders WHERE order_type = 'ff_vip_panel'"
                )
            ).fetchone()
        )[0]
        steam_orders = (await (await db.execute("SELECT COUNT(*) FROM steam_orders")).fetchone())[0]
        tg_service_orders = (
            await (
                await db.execute(
                    """SELECT COUNT(*) FROM settings_orders
                       WHERE order_type IN ('telegram_stars', 'telegram_premium')"""
                )
            ).fetchone()
        )[0]
        pending_all = (
            await (
                await db.execute(
                    """
                    SELECT
                      (SELECT COUNT(*) FROM orders WHERE status='pending')
                    + (SELECT COUNT(*) FROM br_orders WHERE status='pending')
                    + (SELECT COUNT(*) FROM steam_orders WHERE status='pending')
                    + (SELECT COUNT(*) FROM settings_orders WHERE status='pending')
                    + (SELECT COUNT(*) FROM standoff_orders WHERE status='pending')
                    + (SELECT COUNT(*) FROM roulette_tickets WHERE status='pending')
                    """
                )
            ).fetchone()
        )[0]
        accepted_all = (
            await (
                await db.execute(
                    """
                    SELECT
                      (SELECT COUNT(*) FROM orders WHERE status='accepted')
                    + (SELECT COUNT(*) FROM br_orders WHERE status='accepted')
                    + (SELECT COUNT(*) FROM steam_orders WHERE status='accepted')
                    + (SELECT COUNT(*) FROM settings_orders WHERE status='accepted')
                    + (SELECT COUNT(*) FROM standoff_orders WHERE status='accepted')
                    + (SELECT COUNT(*) FROM roulette_tickets WHERE status='accepted')
                    """
                )
            ).fetchone()
        )[0]
        rejected_all = (
            await (
                await db.execute(
                    """
                    SELECT
                      (SELECT COUNT(*) FROM orders WHERE status='rejected')
                    + (SELECT COUNT(*) FROM br_orders WHERE status='rejected')
                    + (SELECT COUNT(*) FROM steam_orders WHERE status='rejected')
                    + (SELECT COUNT(*) FROM settings_orders WHERE status='rejected')
                    + (SELECT COUNT(*) FROM standoff_orders WHERE status='rejected')
                    + (SELECT COUNT(*) FROM roulette_tickets WHERE status='rejected')
                    """
                )
            ).fetchone()
        )[0]
        users_7d = (
            await (
                await db.execute(
                    """SELECT COUNT(*) FROM users
                       WHERE datetime(joined_at) >= datetime('now', '-7 days')"""
                )
            ).fetchone()
        )[0]
        users_24h = (
            await (
                await db.execute(
                    """SELECT COUNT(*) FROM users
                       WHERE datetime(joined_at) >= datetime('now', '-1 day')"""
                )
            ).fetchone()
        )[0]
        active_24h = (
            await (
                await db.execute(
                    """SELECT COUNT(*) FROM users
                       WHERE last_active IS NOT NULL
                         AND datetime(last_active) >= datetime('now', '-1 day')"""
                )
            ).fetchone()
        )[0]
        referrals_total = (
            await (await db.execute("SELECT COUNT(*) FROM referrals")).fetchone()
        )[0]
        standoff_orders_n = (
            await (await db.execute("SELECT COUNT(*) FROM standoff_orders")).fetchone()
        )[0]
        tournaments_open = (
            await (
                await db.execute(
                    "SELECT COUNT(*) FROM tournaments WHERE status IN ('open', 'draft')"
                )
            ).fetchone()
        )[0]
        start_commands = 0
        sc_row = await (
            await db.execute(
                "SELECT value FROM bot_metrics WHERE key = 'start_commands' LIMIT 1"
            )
        ).fetchone()
        if sc_row and sc_row[0] is not None:
            start_commands = int(sc_row[0])
        orders_all = int(pending_all) + int(accepted_all) + int(rejected_all)
        revenue_all_row = await (
            await db.execute(
                """
                SELECT COALESCE(
                  (SELECT SUM(price_tjs) FROM orders WHERE status='accepted'), 0)
                + COALESCE(
                  (SELECT SUM(amount_tjs) FROM steam_orders WHERE status='accepted'), 0)
                + COALESCE(
                  (SELECT SUM(price_tjs) FROM settings_orders WHERE status='accepted'), 0)
                + COALESCE(
                  (SELECT SUM(price_tjs) FROM standoff_orders WHERE status='accepted'), 0)
                + COALESCE(
                  (SELECT SUM(price_tjs) FROM roulette_tickets WHERE status='accepted'), 0)
                + COALESCE(
                  (SELECT SUM(amount) FROM br_orders WHERE status='accepted'), 0)
                AS s
                """
            )
        ).fetchone()
        revenue_all = float(revenue_all_row[0] or 0) if revenue_all_row else 0.0
    return {
        "users": int(users),
        "orders_total": int(orders_total),
        "pending": int(pending),
        "accepted": int(accepted),
        "rejected": int(rejected),
        "revenue_tjs": revenue,
        "ff_settings_orders": int(ff_settings_orders),
        "vip_orders": int(vip_orders),
        "br_orders": int(br_orders),
        "steam_orders": int(steam_orders),
        "tg_service_orders": int(tg_service_orders),
        "pending_all": int(pending_all),
        "accepted_all": int(accepted_all),
        "rejected_all": int(rejected_all),
        "users_7d": int(users_7d),
        "users_24h": int(users_24h),
        "active_24h": int(active_24h),
        "referrals_total": int(referrals_total),
        "standoff_orders": int(standoff_orders_n),
        "tournaments_open": int(tournaments_open),
        "orders_all": int(orders_all),
        "revenue_all_tjs": revenue_all,
        "start_commands": int(start_commands),
    }


async def get_all_users_tg_ids() -> List[int]:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute("SELECT tg_id FROM users")
        rows = await cur.fetchall()
        return [int(r[0]) for r in rows]


async def insert_game(
    name: str,
    emoji: str,
    cover_path: Optional[str] = None,
) -> int:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            """INSERT INTO games(name, emoji, cover_path, is_active)
               VALUES(?,?,?,1)""",
            (name, emoji, cover_path),
        )
        await db.commit()
        return int(cur.lastrowid)


async def update_game(
    game_id: int,
    name: Optional[str] = None,
    emoji: Optional[str] = None,
    cover_path: Optional[str] = None,
    is_active: Optional[int] = None,
) -> None:
    fields: List[str] = []
    vals: List[Any] = []
    if name is not None:
        fields.append("name = ?")
        vals.append(name)
    if emoji is not None:
        fields.append("emoji = ?")
        vals.append(emoji)
    if cover_path is not None:
        fields.append("cover_path = ?")
        vals.append(cover_path)
    if is_active is not None:
        fields.append("is_active = ?")
        vals.append(is_active)
    if not fields:
        return
    vals.append(game_id)
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            f"UPDATE games SET {', '.join(fields)} WHERE id = ?",
            vals,
        )
        await db.commit()


async def delete_game(game_id: int) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("DELETE FROM products WHERE game_id = ?", (game_id,))
        await db.execute("DELETE FROM games WHERE id = ?", (game_id,))
        await db.commit()


async def insert_product(
    game_id: int,
    label: str,
    price_tjs: float,
    is_popular: int = 0,
    is_best_value: int = 0,
    sort_order: int = 0,
    subcategory: str = "cis",
) -> int:
    sub = (subcategory or "cis").strip().lower() or "cis"
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            """INSERT INTO products(
                game_id, label, price_tjs, is_popular, is_best_value, is_active, sort_order, subcategory
            ) VALUES(?,?,?,?,?,1,?,?)""",
            (game_id, label, price_tjs, is_popular, is_best_value, sort_order, sub),
        )
        await db.commit()
        return int(cur.lastrowid)


async def update_product(
    product_id: int,
    label: Optional[str] = None,
    price_tjs: Optional[float] = None,
    is_popular: Optional[int] = None,
    is_best_value: Optional[int] = None,
    is_active: Optional[int] = None,
    sort_order: Optional[int] = None,
) -> None:
    fields: List[str] = []
    vals: List[Any] = []
    if label is not None:
        fields.append("label = ?")
        vals.append(label)
    if price_tjs is not None:
        fields.append("price_tjs = ?")
        vals.append(price_tjs)
    if is_popular is not None:
        fields.append("is_popular = ?")
        vals.append(is_popular)
    if is_best_value is not None:
        fields.append("is_best_value = ?")
        vals.append(is_best_value)
    if is_active is not None:
        fields.append("is_active = ?")
        vals.append(is_active)
    if sort_order is not None:
        fields.append("sort_order = ?")
        vals.append(sort_order)
    if not fields:
        return
    vals.append(product_id)
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            f"UPDATE products SET {', '.join(fields)} WHERE id = ?",
            vals,
        )
        await db.commit()


async def delete_product(product_id: int) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        await db.commit()


async def insert_broadcast(text: str, sent_count: int) -> int:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            "INSERT INTO broadcasts(text, sent_count) VALUES(?,?)",
            (text, sent_count),
        )
        await db.commit()
        return int(cur.lastrowid)


async def add_referral(referrer_id: int, referred_id: int) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            """INSERT OR IGNORE INTO referrals(referrer_id, referred_id)
               VALUES(?,?)""",
            (referrer_id, referred_id),
        )
        await db.commit()


async def get_referral(referred_id: int) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM referrals WHERE referred_id = ?",
            (referred_id,),
        )
        row = await cur.fetchone()
        return _row_to_dict(row) if row else None


async def count_referrals(referrer_id: int) -> int:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM referrals WHERE referrer_id = ?",
            (referrer_id,),
        )
        row = await cur.fetchone()
        return int(row[0]) if row else 0


async def create_settings_order(
    user_tg_id: int,
    username: Optional[str],
    order_type: str,
    phone_model: str,
    price_tjs: float,
    payment_method: str,
    receipt_file_id: str,
) -> int:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            """INSERT INTO settings_orders(
                user_tg_id, username, order_type, phone_model, price_tjs,
                payment_method, receipt_file_id, status
            ) VALUES(?,?,?,?,?,?,?,'pending')""",
            (
                user_tg_id,
                username,
                order_type,
                phone_model,
                price_tjs,
                payment_method,
                receipt_file_id,
            ),
        )
        await db.commit()
        return int(cur.lastrowid)


async def get_settings_order(order_id: int) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM settings_orders WHERE id = ?", (order_id,))
        row = await cur.fetchone()
        return _row_to_dict(row) if row else None


async def get_settings_orders_by_status(status: Optional[str]) -> List[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cur = await db.execute(
                "SELECT * FROM settings_orders WHERE status = ? ORDER BY id DESC",
                (status,),
            )
        else:
            cur = await db.execute("SELECT * FROM settings_orders ORDER BY id DESC")
        rows = await cur.fetchall()
        return [_row_to_dict(r) for r in rows]


async def update_settings_order_status(order_id: int, status: str) -> None:
    completed_at = datetime.utcnow().isoformat(timespec="seconds") if status != "pending" else None
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "UPDATE settings_orders SET status = ?, completed_at = ? WHERE id = ?",
            (status, completed_at, order_id),
        )
        await db.commit()


async def update_settings_order_text(order_id: int, settings_text: str) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "UPDATE settings_orders SET settings_text = ? WHERE id = ?",
            (settings_text, order_id),
        )
        await db.commit()


async def update_vip_file(order_id: int, file_id: str) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "UPDATE settings_orders SET vip_file_id = ? WHERE id = ?",
            (file_id, order_id),
        )
        await db.commit()


async def delete_settings_order(order_id: int) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("DELETE FROM settings_orders WHERE id = ?", (order_id,))
        await db.commit()


async def create_br_order(
    user_tg_id: int,
    username: Optional[str],
    server_name: str,
    nickname: str,
    amount: float,
    payment_method: str,
    receipt_file_id: str,
) -> int:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            """INSERT INTO br_orders(
                user_tg_id, username, server_name, nickname, amount,
                payment_method, receipt_file_id, status
            ) VALUES(?,?,?,?,?,?,?,'pending')""",
            (
                user_tg_id,
                username,
                server_name,
                nickname,
                amount,
                payment_method,
                receipt_file_id,
            ),
        )
        await db.commit()
        return int(cur.lastrowid)


async def get_br_order(order_id: int) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM br_orders WHERE id = ?", (order_id,))
        row = await cur.fetchone()
        return _row_to_dict(row) if row else None


async def get_br_orders_by_status(status: Optional[str]) -> List[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cur = await db.execute(
                "SELECT * FROM br_orders WHERE status = ? ORDER BY id DESC",
                (status,),
            )
        else:
            cur = await db.execute("SELECT * FROM br_orders ORDER BY id DESC")
        rows = await cur.fetchall()
        return [_row_to_dict(r) for r in rows]


async def update_br_order_status(order_id: int, status: str) -> None:
    completed_at = datetime.utcnow().isoformat(timespec="seconds") if status != "pending" else None
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "UPDATE br_orders SET status = ?, completed_at = ? WHERE id = ?",
            (status, completed_at, order_id),
        )
        await db.commit()


async def delete_br_order(order_id: int) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("DELETE FROM br_orders WHERE id = ?", (order_id,))
        await db.commit()


async def get_setting(key: str) -> str | None:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cur.fetchone()
        return str(row[0]) if row and row[0] is not None else None


async def set_setting(key: str, value: str) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            """INSERT INTO settings(key, value, updated_at)
               VALUES(?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(key) DO UPDATE SET
                 value=excluded.value,
                 updated_at=CURRENT_TIMESTAMP""",
            (key, value),
        )
        await db.commit()


async def get_db_admin_ids() -> List[int]:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute("SELECT user_id FROM admins")
        rows = await cur.fetchall()
        return [int(r[0]) for r in rows]


async def get_admins_full() -> List[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT user_id, username, added_by, created_at FROM admins ORDER BY created_at"
        )
        return [_row_to_dict(r) for r in await cur.fetchall()]


async def add_admin(
    user_id: int,
    username: Optional[str] = None,
    added_by: Optional[int] = None,
) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            """INSERT INTO admins(user_id, username, added_by)
               VALUES(?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET username=excluded.username""",
            (int(user_id), username, added_by),
        )
        await db.commit()


async def remove_admin(user_id: int) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("DELETE FROM admins WHERE user_id = ?", (int(user_id),))
        await db.commit()


async def user_exists(tg_id: int) -> bool:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute("SELECT 1 FROM users WHERE tg_id = ? LIMIT 1", (tg_id,))
        return await cur.fetchone() is not None


# Таблицы со всеми типами заказов — для агрегированной статистики по периодам.
# Имена жёстко зашиты в коде (не из пользовательского ввода) => безопасно для f-строк.
_ALL_ORDER_TABLES = (
    "orders",
    "br_orders",
    "steam_orders",
    "settings_orders",
    "standoff_orders",
    "roulette_tickets",
    "ai_sub_orders",
)


async def get_period_stats() -> dict[str, dict[str, int]]:
    """Кол-во новых пользователей и заказов за окна: 7д, 30д, 130д, год, всё время."""
    windows: dict[str, Optional[str]] = {
        "7d": "-7 days",
        "30d": "-30 days",
        "130d": "-130 days",
        "year": "-365 days",
        "all": None,
    }
    result: dict[str, dict[str, int]] = {}
    async with aiosqlite.connect(get_db_path()) as db:
        for key, modifier in windows.items():
            if modifier:
                users_row = await (
                    await db.execute(
                        "SELECT COUNT(*) FROM users "
                        "WHERE datetime(joined_at) >= datetime('now', ?)",
                        (modifier,),
                    )
                ).fetchone()
            else:
                users_row = await (
                    await db.execute("SELECT COUNT(*) FROM users")
                ).fetchone()
            users_count = int(users_row[0]) if users_row else 0

            orders_count = 0
            for table in _ALL_ORDER_TABLES:
                try:
                    if modifier:
                        row = await (
                            await db.execute(
                                f"SELECT COUNT(*) FROM {table} "
                                "WHERE datetime(created_at) >= datetime('now', ?)",
                                (modifier,),
                            )
                        ).fetchone()
                    else:
                        row = await (
                            await db.execute(f"SELECT COUNT(*) FROM {table}")
                        ).fetchone()
                    orders_count += int(row[0]) if row else 0
                except Exception:
                    continue
            result[key] = {"users": users_count, "orders": orders_count}
    return result


async def create_steam_order(
    user_tg_id: int,
    username: str | None,
    steam_login: str,
    amount_usd: float,
    amount_tjs: float,
    usd_rate: float,
    payment_method: str,
    receipt_file_id: str,
) -> int:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            """INSERT INTO steam_orders(
                user_tg_id, username, steam_login, amount_usd, amount_tjs, usd_rate,
                payment_method, receipt_file_id, status
            ) VALUES(?,?,?,?,?,?,?,?, 'pending')""",
            (
                user_tg_id,
                username,
                steam_login,
                amount_usd,
                amount_tjs,
                usd_rate,
                payment_method,
                receipt_file_id,
            ),
        )
        await db.commit()
        return int(cur.lastrowid)


async def get_steam_order(order_id: int) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM steam_orders WHERE id = ?", (order_id,))
        row = await cur.fetchone()
        return _row_to_dict(row) if row else None


async def get_steam_orders_by_status(status: Optional[str]) -> list[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cur = await db.execute(
                "SELECT * FROM steam_orders WHERE status = ? ORDER BY id DESC",
                (status,),
            )
        else:
            cur = await db.execute("SELECT * FROM steam_orders ORDER BY id DESC")
        rows = await cur.fetchall()
        return [_row_to_dict(r) for r in rows]


async def update_steam_order_status(order_id: int, status: str) -> None:
    completed_at = datetime.utcnow().isoformat(timespec="seconds") if status != "pending" else None
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "UPDATE steam_orders SET status = ?, completed_at = ? WHERE id = ?",
            (status, completed_at, order_id),
        )
        await db.commit()


async def delete_steam_order(order_id: int) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("DELETE FROM steam_orders WHERE id = ?", (order_id,))
        await db.commit()


async def create_ai_sub_order(
    user_tg_id: int,
    username: str | None,
    service_name: str,
    service_key: str,
    plan_name: str,
    price_usd: float,
    price_tjs: float,
    usd_rate: float,
    payment_method: str,
    receipt_file_id: str,
    period: str = "1 месяц",
) -> int:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            """INSERT INTO ai_sub_orders(
                user_tg_id, username, service_name, service_key, plan_name,
                price_usd, price_tjs, usd_rate, period,
                payment_method, receipt_file_id, status
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?, 'pending')""",
            (
                user_tg_id,
                username,
                service_name,
                service_key,
                plan_name,
                price_usd,
                price_tjs,
                usd_rate,
                period,
                payment_method,
                receipt_file_id,
            ),
        )
        await db.commit()
        return int(cur.lastrowid)


async def get_ai_sub_order(order_id: int) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM ai_sub_orders WHERE id = ?", (order_id,))
        row = await cur.fetchone()
        return _row_to_dict(row) if row else None


async def get_ai_sub_orders_by_status(status: Optional[str]) -> list[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cur = await db.execute(
                "SELECT * FROM ai_sub_orders WHERE status = ? ORDER BY id DESC",
                (status,),
            )
        else:
            cur = await db.execute("SELECT * FROM ai_sub_orders ORDER BY id DESC")
        rows = await cur.fetchall()
        return [_row_to_dict(r) for r in rows]


async def update_ai_sub_order_status(order_id: int, status: str) -> None:
    completed_at = datetime.utcnow().isoformat(timespec="seconds") if status != "pending" else None
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "UPDATE ai_sub_orders SET status = ?, completed_at = ? WHERE id = ?",
            (status, completed_at, order_id),
        )
        await db.commit()


async def delete_ai_sub_order(order_id: int) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("DELETE FROM ai_sub_orders WHERE id = ?", (order_id,))
        await db.commit()


async def get_ticket_order(order_id: int) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM roulette_tickets WHERE id = ?", (order_id,))
        row = await cur.fetchone()
        return _row_to_dict(row) if row else None


async def get_all_orders_counts() -> dict[str, int]:
    async with aiosqlite.connect(get_db_path()) as db:
        result: dict[str, int] = {"pending": 0, "accepted": 0, "rejected": 0}
        for st in ("pending", "accepted", "rejected"):
            cur = await db.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM orders WHERE status = ?)
                  + (SELECT COUNT(*) FROM br_orders WHERE status = ?)
                  + (SELECT COUNT(*) FROM steam_orders WHERE status = ?)
                  + (SELECT COUNT(*) FROM settings_orders WHERE status = ?)
                  + (SELECT COUNT(*) FROM roulette_tickets WHERE status = ?)
                  + (SELECT COUNT(*) FROM standoff_orders WHERE status = ?)
                  + (SELECT COUNT(*) FROM ai_sub_orders WHERE status = ?)
                """,
                (st, st, st, st, st, st, st),
            )
            row = await cur.fetchone()
            result[st] = int(row[0]) if row else 0
        return result


async def get_all_orders_paginated(status: str, page: int, limit: int = 8) -> list[dict[str, Any]]:
    offset = page * limit
    sql = """
      SELECT id, user_tg_id, username,
             'ff' as game_type,
             product_label as item,
             CAST(price_tjs as TEXT)||' смн' as amount_str,
             status, created_at
      FROM orders
      WHERE status=?
      UNION ALL
      SELECT id, user_tg_id, username,
             'br' as game_type,
             'BR:'||server_name as item,
             CAST(amount as TEXT)||' ₽' as amount_str,
             status, created_at
      FROM br_orders
      WHERE status=?
      UNION ALL
      SELECT id, user_tg_id, username,
             'steam' as game_type,
             'Steam:'||steam_login as item,
             CAST(amount_usd as TEXT)||'$' as amount_str,
             status, created_at
      FROM steam_orders
      WHERE status=?
      UNION ALL
      SELECT id, user_tg_id, username,
             'settings' as game_type,
             order_type as item,
             CAST(price_tjs as TEXT)||' смн' as amount_str,
             status, created_at
      FROM settings_orders
      WHERE status=?
      UNION ALL
      SELECT id, user_tg_id, username,
             'tickets' as game_type,
             CAST(ticket_count as TEXT)||' билетов' as item,
             CAST(price_tjs as TEXT)||' смн' as amount_str,
             status, created_at
      FROM roulette_tickets
      WHERE status=?
      UNION ALL
      SELECT id, user_tg_id, username,
             'standoff' as game_type,
             product_label as item,
             CAST(price_tjs as TEXT)||' смн' as amount_str,
             status, created_at
      FROM standoff_orders
      WHERE status=?
      UNION ALL
      SELECT id, user_tg_id, username,
             'ai_sub' as game_type,
             service_name||' '||plan_name as item,
             CAST(price_usd as TEXT)||'$' as amount_str,
             status, created_at
      FROM ai_sub_orders
      WHERE status=?
      ORDER BY created_at DESC
      LIMIT ? OFFSET ?
    """
    params = (status,) * 7 + (limit, offset)
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(sql, params)
        rows = await cur.fetchall()
        return [_row_to_dict(r) for r in rows]


async def get_required_channels() -> List[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT id, channel_ref, created_at FROM required_channels ORDER BY id DESC"
        )
        rows = await cur.fetchall()
        return [_row_to_dict(r) for r in rows]


async def add_required_channel(channel_ref: str) -> int:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            "INSERT OR IGNORE INTO required_channels(channel_ref) VALUES(?)",
            (channel_ref.strip(),),
        )
        await db.commit()
        return int(cur.lastrowid or 0)


async def delete_required_channel(channel_id: int) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("DELETE FROM required_channels WHERE id = ?", (channel_id,))
        await db.commit()


async def create_standoff_order(
    user_tg_id: int,
    username: Optional[str],
    product_label: str,
    price_tjs: float,
    game_account_id: str,
    payment_method: str,
    receipt_file_id: str,
    gold_amount: Optional[int] = None,
    is_manual: int = 0,
) -> int:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            """INSERT INTO standoff_orders(
                user_tg_id, username, product_label, price_tjs, game_account_id,
                gold_amount, is_manual, payment_method, receipt_file_id, status
            ) VALUES(?,?,?,?,?,?,?,?,?,'pending')""",
            (
                user_tg_id,
                username,
                product_label,
                price_tjs,
                game_account_id,
                gold_amount,
                is_manual,
                payment_method,
                receipt_file_id,
            ),
        )
        await db.commit()
        return int(cur.lastrowid)


async def get_standoff_order(order_id: int) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM standoff_orders WHERE id = ?", (order_id,))
        row = await cur.fetchone()
        return _row_to_dict(row) if row else None


async def update_standoff_order_status(order_id: int, status: str) -> None:
    completed_at = datetime.utcnow().isoformat(timespec="seconds") if status != "pending" else None
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "UPDATE standoff_orders SET status = ?, completed_at = ? WHERE id = ?",
            (status, completed_at, order_id),
        )
        await db.commit()


async def delete_standoff_order(order_id: int) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("DELETE FROM standoff_orders WHERE id = ?", (order_id,))
        await db.commit()


async def update_roulette_ticket_status(order_id: int, status: str) -> None:
    completed_at = datetime.utcnow().isoformat(timespec="seconds") if status != "pending" else None
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "UPDATE roulette_tickets SET status = ?, completed_at = ? WHERE id = ?",
            (status, completed_at, order_id),
        )
        await db.commit()


async def delete_roulette_ticket_order(order_id: int) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("DELETE FROM roulette_tickets WHERE id = ?", (order_id,))
        await db.commit()


async def update_order_status_by_type(game_type: str, order_id: int, status: str) -> None:
    if game_type == "ff":
        await update_order_status(order_id, status, completed=status != "pending")
    elif game_type == "steam":
        await update_steam_order_status(order_id, status)
    elif game_type == "br":
        await update_br_order_status(order_id, status)
    elif game_type == "settings":
        await update_settings_order_status(order_id, status)
    elif game_type == "tickets":
        await update_roulette_ticket_status(order_id, status)
    elif game_type == "standoff":
        await update_standoff_order_status(order_id, status)
    elif game_type == "ai_sub":
        await update_ai_sub_order_status(order_id, status)


async def get_total_spent_tjs(user_tg_id: int) -> float:
    """Sum of accepted order amounts in смн (BR amount included as numeric contribution)."""
    uid = int(user_tg_id)
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            """
            SELECT COALESCE(
              (SELECT SUM(price_tjs) FROM orders WHERE user_tg_id = ? AND status = 'accepted'), 0)
            + COALESCE(
              (SELECT SUM(amount_tjs) FROM steam_orders WHERE user_tg_id = ? AND status = 'accepted'), 0)
            + COALESCE(
              (SELECT SUM(price_tjs) FROM settings_orders WHERE user_tg_id = ? AND status = 'accepted'), 0)
            + COALESCE(
              (SELECT SUM(price_tjs) FROM standoff_orders WHERE user_tg_id = ? AND status = 'accepted'), 0)
            + COALESCE(
              (SELECT SUM(price_tjs) FROM roulette_tickets WHERE user_tg_id = ? AND status = 'accepted'), 0)
            + COALESCE(
              (SELECT SUM(amount) FROM br_orders WHERE user_tg_id = ? AND status = 'accepted'), 0)
            + COALESCE(
              (SELECT SUM(price_tjs) FROM ai_sub_orders WHERE user_tg_id = ? AND status = 'accepted'), 0)
            AS s
            """,
            (uid, uid, uid, uid, uid, uid, uid),
        )
        row = await cur.fetchone()
        return float(row[0] or 0) if row else 0.0


async def get_bonus_balance(user_tg_id: int) -> float:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            "SELECT balance FROM bonus_balance WHERE user_tg_id = ?",
            (user_tg_id,),
        )
        row = await cur.fetchone()
        return float(row[0]) if row and row[0] is not None else 0.0


async def add_bonus_balance(user_tg_id: int, delta: float) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            """INSERT INTO bonus_balance(user_tg_id, balance)
               VALUES(?, ?)
               ON CONFLICT(user_tg_id) DO UPDATE SET
                 balance = balance + excluded.balance""",
            (user_tg_id, delta),
        )
        await db.commit()


async def has_bonus_for_level(user_tg_id: int, level_key: str) -> bool:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            """SELECT 1 FROM bonus_history
               WHERE user_tg_id = ? AND reason = ? LIMIT 1""",
            (user_tg_id, level_key),
        )
        row = await cur.fetchone()
        return row is not None


async def record_bonus(user_tg_id: int, delta: float, reason: str) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            """INSERT INTO bonus_history(user_tg_id, delta, reason, created_at)
               VALUES(?,?,?,?)""",
            (user_tg_id, delta, reason, now),
        )
        await db.commit()


async def create_tournament(
    title: str,
    description: str,
    max_players: int,
    status: str = "open",
) -> int:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            """INSERT INTO tournaments(title, description, max_players, status)
               VALUES(?,?,?,?)""",
            (title, description, int(max_players), status),
        )
        await db.commit()
        return int(cur.lastrowid)


async def get_tournament(tournament_id: int) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM tournaments WHERE id = ?", (tournament_id,))
        row = await cur.fetchone()
        return _row_to_dict(row) if row else None


async def list_tournaments_by_status(status: str) -> List[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM tournaments WHERE status = ? ORDER BY id DESC",
            (status,),
        )
        rows = await cur.fetchall()
        return [_row_to_dict(r) for r in rows]


async def list_all_tournaments_admin() -> List[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM tournaments ORDER BY id DESC")
        rows = await cur.fetchall()
        return [_row_to_dict(r) for r in rows]


async def set_tournament_status(tournament_id: int, status: str) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "UPDATE tournaments SET status = ? WHERE id = ?",
            (status, tournament_id),
        )
        await db.commit()


async def delete_tournament(tournament_id: int) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "DELETE FROM tournament_registrations WHERE tournament_id = ?",
            (tournament_id,),
        )
        await db.execute("DELETE FROM tournaments WHERE id = ?", (tournament_id,))
        await db.commit()


async def set_tournament_launch(
    tournament_id: int,
    room_id: str,
    room_password: str,
    channel_message_id: Optional[int] = None,
) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            """UPDATE tournaments SET room_id = ?, room_password = ?,
               channel_message_id = ?, status = 'launched', launched_at = ?
               WHERE id = ?""",
            (room_id, room_password, channel_message_id, now, tournament_id),
        )
        await db.commit()


async def count_tournament_registrations(tournament_id: int) -> int:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM tournament_registrations WHERE tournament_id = ?",
            (tournament_id,),
        )
        row = await cur.fetchone()
        return int(row[0]) if row else 0


async def register_tournament_user(
    tournament_id: int,
    user_tg_id: int,
    username: Optional[str],
    game_nickname: str,
) -> bool:
    try:
        async with aiosqlite.connect(get_db_path()) as db:
            await db.execute(
                """INSERT INTO tournament_registrations(
                    tournament_id, user_tg_id, username, game_nickname
                ) VALUES(?,?,?,?)""",
                (tournament_id, user_tg_id, username, game_nickname),
            )
            await db.commit()
        return True
    except aiosqlite.IntegrityError:
        return False


async def is_user_registered_tournament(tournament_id: int, user_tg_id: int) -> bool:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            """SELECT 1 FROM tournament_registrations
               WHERE tournament_id = ? AND user_tg_id = ? LIMIT 1""",
            (tournament_id, user_tg_id),
        )
        row = await cur.fetchone()
        return row is not None


async def get_tournament_registrations_page(
    tournament_id: int,
    page: int,
    limit: int = 20,
) -> List[dict[str, Any]]:
    offset = max(0, page) * limit
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT * FROM tournament_registrations
               WHERE tournament_id = ?
               ORDER BY id ASC
               LIMIT ? OFFSET ?""",
            (tournament_id, limit, offset),
        )
        rows = await cur.fetchall()
        return [_row_to_dict(r) for r in rows]


async def get_tournament_registration_user_ids(tournament_id: int) -> List[int]:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            "SELECT user_tg_id FROM tournament_registrations WHERE tournament_id = ?",
            (tournament_id,),
        )
        rows = await cur.fetchall()
        return [int(r[0]) for r in rows]


# --- Anti-spam in-memory helpers (optional use from middleware) ---
async def count_all_users() -> int:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        row = await cur.fetchone()
        return int(row[0]) if row else 0


async def count_banned_users() -> int:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            """SELECT COUNT(*) FROM banned_users
               WHERE unbanned_at IS NULL"""
        )
        row = await cur.fetchone()
        return int(row[0]) if row else 0


async def get_user_by_id(tg_id: int) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE tg_id = ?", (int(tg_id),))
        row = await cur.fetchone()
        return _row_to_dict(row) if row else None


async def get_user_by_username(username: str) -> Optional[dict[str, Any]]:
    uname = (username or "").strip().lstrip("@").lower()
    if not uname:
        return None
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT * FROM users
               WHERE LOWER(TRIM(username)) = ? COLLATE NOCASE
               LIMIT 1""",
            (uname,),
        )
        row = await cur.fetchone()
        return _row_to_dict(row) if row else None


async def is_user_banned(tg_id: int) -> bool:
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            "SELECT is_banned FROM users WHERE tg_id = ?",
            (int(tg_id),),
        )
        row = await cur.fetchone()
        if row and int(row[0] or 0) == 1:
            return True
        cur2 = await db.execute(
            """SELECT 1 FROM banned_users
               WHERE tg_id = ? AND unbanned_at IS NULL LIMIT 1""",
            (int(tg_id),),
        )
        return await cur2.fetchone() is not None


async def get_banned_user(tg_id: int) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT * FROM banned_users
               WHERE tg_id = ? AND unbanned_at IS NULL
               ORDER BY id DESC LIMIT 1""",
            (int(tg_id),),
        )
        row = await cur.fetchone()
        return _row_to_dict(row) if row else None


async def get_all_banned_users() -> list[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT * FROM banned_users
               WHERE unbanned_at IS NULL
               ORDER BY banned_at DESC"""
        )
        rows = await cur.fetchall()
        return [_row_to_dict(r) for r in rows]


async def ban_user(
    tg_id: int,
    username: str | None,
    first_name: str | None,
    reason: str,
    admin_id: int,
) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            """INSERT INTO banned_users(
                tg_id, username, first_name, reason, banned_by, banned_at, unbanned_at
            ) VALUES(?,?,?,?,?,?,NULL)
            ON CONFLICT(tg_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                reason=excluded.reason,
                banned_by=excluded.banned_by,
                banned_at=excluded.banned_at,
                unbanned_at=NULL""",
            (int(tg_id), username, first_name, reason, int(admin_id), now),
        )
        await db.execute(
            "UPDATE users SET is_banned = 1 WHERE tg_id = ?",
            (int(tg_id),),
        )
        await db.commit()


async def unban_user(tg_id: int, admin_id: int) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            """UPDATE banned_users SET unbanned_at = ?
               WHERE tg_id = ? AND unbanned_at IS NULL""",
            (now, int(tg_id)),
        )
        await db.execute(
            "UPDATE users SET is_banned = 0 WHERE tg_id = ?",
            (int(tg_id),),
        )
        await db.commit()


async def add_ban_history(
    tg_id: int,
    action: str,
    reason: str,
    admin_id: int,
) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            """INSERT INTO ban_history(tg_id, action, reason, admin_id)
               VALUES(?,?,?,?)""",
            (int(tg_id), action, reason, int(admin_id)),
        )
        await db.commit()


async def get_ban_history(tg_id: int) -> list[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT * FROM ban_history
               WHERE tg_id = ?
               ORDER BY created_at ASC""",
            (int(tg_id),),
        )
        rows = await cur.fetchall()
        return [_row_to_dict(r) for r in rows]


async def get_user_orders_count(tg_id: int) -> int:
    uid = int(tg_id)
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM orders WHERE user_tg_id = ?)
            + (SELECT COUNT(*) FROM br_orders WHERE user_tg_id = ?)
            + (SELECT COUNT(*) FROM steam_orders WHERE user_tg_id = ?)
            + (SELECT COUNT(*) FROM settings_orders WHERE user_tg_id = ?)
            + (SELECT COUNT(*) FROM standoff_orders WHERE user_tg_id = ?)
            + (SELECT COUNT(*) FROM roulette_tickets WHERE user_tg_id = ?)
            + (SELECT COUNT(*) FROM ai_sub_orders WHERE user_tg_id = ?)
            """,
            (uid, uid, uid, uid, uid, uid, uid),
        )
        row = await cur.fetchone()
        return int(row[0] or 0) if row else 0


async def get_user_total_spent(tg_id: int) -> float:
    return await get_total_spent_tjs(tg_id)


async def is_receipt_duplicate(file_unique_id: str) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM receipt_hashes WHERE file_unique_id = ?",
            (file_unique_id,),
        )
        row = await cur.fetchone()
        return _row_to_dict(row) if row else None


async def save_receipt_hash(
    file_unique_id: str,
    file_id: str,
    user_tg_id: int,
    order_type: str,
    order_id: int,
) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            """INSERT OR IGNORE INTO receipt_hashes(
                file_unique_id, file_id, user_tg_id, order_type, order_id
            ) VALUES(?,?,?,?,?)""",
            (file_unique_id, file_id, int(user_tg_id), order_type, int(order_id)),
        )
        await db.commit()


def _parse_free_settings_given_at(val: Any) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        dt = val
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    s = str(val).strip()
    if " " in s and "T" not in s:
        s = s.replace(" ", "T", 1)
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def get_last_settings_request(user_tg_id: int) -> datetime | None:
    """Возвращает время последнего запроса настроек."""
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            """SELECT given_at FROM free_settings_log
               WHERE user_tg_id=? ORDER BY given_at DESC LIMIT 1""",
            (int(user_tg_id),),
        )
        row = await cur.fetchone()
        if not row or row[0] is None:
            return None
        return _parse_free_settings_given_at(row[0])


async def save_settings_log(user_tg_id: int, phone_model: str, brand_key: str) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            """INSERT INTO free_settings_log(user_tg_id, phone_model, brand_key)
               VALUES(?,?,?)""",
            (int(user_tg_id), phone_model, brand_key),
        )
        await db.commit()


async def can_get_free_settings(user_tg_id: int) -> tuple[bool, int]:
    """(можно_ли, часов_осталось)"""
    last = await get_last_settings_request(user_tg_id)
    if not last:
        return True, 0
    delta = datetime.now(timezone.utc) - last
    hours_passed = delta.total_seconds() / 3600
    if hours_passed >= 48:
        return True, 0
    hours_left = int(48 - hours_passed) + 1
    return False, hours_left


_spam_buckets: dict[int, list[float]] = {}


def antispam_check(user_id: int, max_events: int = 25, window_sec: float = 15.0) -> bool:
    """Returns True if allowed, False if should block."""
    now = time.time()
    bucket = _spam_buckets.setdefault(user_id, [])
    bucket[:] = [t for t in bucket if now - t < window_sec]
    if len(bucket) >= max_events:
        return False
    bucket.append(now)
    return True

# ✅ ГОТОВО: database/queries.py

