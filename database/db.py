import aiosqlite
from pathlib import Path

from config import config

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_db_path() -> Path:
    p = Path(config.DATABASE_PATH).expanduser()
    if p.is_absolute():
        return p.resolve()
    return (_PROJECT_ROOT / p).resolve()


async def init_db() -> None:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        schema = _SCHEMA_PATH.read_text(encoding="utf-8")
        await db.executescript(schema)
        await db.execute(
            """CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        await db.execute(
            """CREATE TABLE IF NOT EXISTS steam_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_tg_id INTEGER,
                username TEXT,
                steam_login TEXT,
                amount_usd REAL,
                amount_tjs REAL,
                usd_rate REAL,
                payment_method TEXT,
                receipt_file_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME
            )"""
        )
        await db.execute(
            """CREATE TABLE IF NOT EXISTS ai_sub_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_tg_id INTEGER,
                username TEXT,
                service_name TEXT,
                service_key TEXT,
                plan_name TEXT,
                price_usd REAL,
                price_tjs REAL,
                usd_rate REAL,
                period TEXT DEFAULT '1 месяц',
                payment_method TEXT,
                receipt_file_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME
            )"""
        )
        await db.execute(
            """CREATE TABLE IF NOT EXISTS required_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_ref TEXT NOT NULL UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        await db.execute(
            """CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                added_by INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        await db.execute(
            """CREATE TABLE IF NOT EXISTS banned_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE,
                username TEXT,
                first_name TEXT,
                reason TEXT,
                banned_by INTEGER,
                banned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                unbanned_at DATETIME
            )"""
        )
        await db.execute(
            """CREATE TABLE IF NOT EXISTS ban_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER,
                action TEXT,
                reason TEXT,
                admin_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        await db.execute(
            """CREATE TABLE IF NOT EXISTS receipt_hashes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_unique_id TEXT UNIQUE,
                file_id TEXT,
                user_tg_id INTEGER,
                order_type TEXT,
                order_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        await db.execute(
            """CREATE TABLE IF NOT EXISTS free_settings_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_tg_id INTEGER,
                phone_model TEXT,
                brand_key TEXT,
                given_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        await db.execute(
            """CREATE INDEX IF NOT EXISTS idx_settings_user
               ON free_settings_log(user_tg_id, given_at)"""
        )
        await db.commit()

        cur_u = await db.execute("PRAGMA table_info(users)")
        user_cols = [r[1] for r in await cur_u.fetchall()]
        if user_cols and "is_banned" not in user_cols:
            await db.execute(
                "ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0"
            )
            await db.commit()

        cur_cols = await db.execute("PRAGMA table_info(referrals)")
        ref_cols = [r[1] for r in await cur_cols.fetchall()]
        if ref_cols and "has_purchased" in ref_cols:
            await db.executescript(
                """
                CREATE TABLE referrals__migr (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER NOT NULL UNIQUE,
                    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                INSERT OR IGNORE INTO referrals__migr (referrer_id, referred_id, joined_at)
                  SELECT referrer_id, referred_id,
                    COALESCE(joined_at, CURRENT_TIMESTAMP) FROM referrals;
                DROP TABLE referrals;
                ALTER TABLE referrals__migr RENAME TO referrals;
                """
            )
            await db.commit()
        await db.execute("DROP TABLE IF EXISTS referral_rewards")
        await db.commit()

        await db.execute(
            """CREATE TABLE IF NOT EXISTS bot_metrics (
                key TEXT PRIMARY KEY,
                value INTEGER NOT NULL DEFAULT 0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        await db.commit()

        cur_m = await db.execute(
            "SELECT 1 FROM settings WHERE key = 'maintenance_mode' LIMIT 1"
        )
        if not await cur_m.fetchone():
            await db.execute(
                "INSERT INTO settings(key, value) VALUES('maintenance_mode', '0')"
            )
            await db.commit()

        cur_p = await db.execute("PRAGMA table_info(products)")
        prod_cols = [r[1] for r in await cur_p.fetchall()]
        if prod_cols and "subcategory" not in prod_cols:
            await db.execute(
                "ALTER TABLE products ADD COLUMN subcategory TEXT DEFAULT 'cis'"
            )
            await db.execute(
                """UPDATE products SET subcategory = 'cis'
                   WHERE subcategory IS NULL OR subcategory = ''"""
            )
            await db.commit()

        cur = await db.execute("SELECT COUNT(*) AS c FROM games")
        row = await cur.fetchone()
        if row and row["c"] == 0:
            ff = config.resolve_optional_path(config.GAME_COVER_FF or None)
            pg = config.resolve_optional_path(config.GAME_COVER_PUBG or None)
            await db.executemany(
                "INSERT INTO games(name, emoji, cover_path, is_active) VALUES(?,?,?,1)",
                [
                    ("Free Fire", "🔥", ff),
                    ("PUBG Mobile", "🎮", pg),
                    ("Black Russia", "🚗", None),
                ],
            )
            await db.executemany(
                """INSERT INTO products(game_id, label, price_tjs, is_popular, is_best_value, is_active, sort_order)
                   VALUES(?,?,?,?,?,1,0)""",
                [
                    (1, "💎 100 алмазов", 11, 0, 0),
                    (1, "💎 310 алмазов", 31, 1, 0),
                    (1, "💎 520 алмазов", 51, 0, 0),
                    (1, "💎 1060 алмазов", 110, 1, 0),
                    (1, "💎 2180 алмазов", 180, 0, 0),
                    (1, "💎 5600 алмазов", 550, 0, 1),
                    (2, "🎮 60 UC", 11, 0, 0),
                    (2, "🎮 120 UC", 22, 0, 0),
                    (2, "🎮 180 UC", 33, 1, 0),
                    (2, "🎮 240 UC", 44, 0, 0),
                    (2, "🎮 325 UC", 51, 0, 0),
                    (2, "🎮 660 UC", 103, 0, 0),
                    (2, "🎮 1800 UC", 283, 0, 0),
                    (2, "🎮 3850 UC", 583, 0, 0),
                    (2, "🎮 8100 UC", 1205, 0, 1),
                ],
            )
            await db.commit()
        cur_br = await db.execute(
            "SELECT COUNT(*) AS c FROM games WHERE LOWER(name) = 'black russia'"
        )
        br_row = await cur_br.fetchone()
        if not br_row or int(br_row["c"]) == 0:
            await db.execute(
                "INSERT INTO games(name, emoji, cover_path, is_active) VALUES('Black Russia','🚗',NULL,1)"
            )
            await db.commit()
        ff_row = await (await db.execute("SELECT id FROM games WHERE LOWER(name)='free fire' LIMIT 1")).fetchone()
        pg_row = await (await db.execute("SELECT id FROM games WHERE LOWER(name)='pubg mobile' LIMIT 1")).fetchone()
        if ff_row:
            ff_id = int(ff_row["id"])
            cur_cis = await db.execute(
                """SELECT COUNT(*) AS c FROM products
                   WHERE game_id = ? AND (subcategory IS NULL OR subcategory = '' OR subcategory = 'cis')""",
                (ff_id,),
            )
            cis_n = int((await cur_cis.fetchone())["c"])
            if cis_n == 0:
                await db.executemany(
                    """INSERT INTO products(
                        game_id, label, price_tjs, is_popular, is_best_value, is_active, sort_order, subcategory
                    ) VALUES(?,?,?,?,?,1,?,?)""",
                    [
                        (ff_id, "💎 100+10 бонус - 110 алм.", 10.50, 0, 0, 1, "cis"),
                        (ff_id, "💎 310+16 бонус - 326 алм.", 31.00, 0, 0, 2, "cis"),
                        (ff_id, "💎 520+24 бонус - 544 алм.", 51.00, 0, 0, 3, "cis"),
                        (ff_id, "💎 1060+53 бонус - 1113 алм.", 104.00, 1, 0, 4, "cis"),
                        (ff_id, "💎 2180+240 бонус - 2420 алм.", 214.00, 0, 0, 5, "cis"),
                        (ff_id, "💎 5600+560 бонус HOT💥 - 6160 алм.", 485.00, 1, 1, 6, "cis"),
                        (ff_id, "🗓️ Ваучер на Неделя +450 💎 - 450 алм.", 17.00, 0, 0, 7, "cis"),
                        (ff_id, "🎫 Ваучер на Месяц - 2600 алм.", 104.00, 0, 0, 8, "cis"),
                        (ff_id, "🎟️ Ваучер на Lite - 90 алм.", 8.00, 0, 0, 9, "cis"),
                        (ff_id, "🎮 Пропуск Прокачка - 1150 алм.", 51.00, 0, 0, 10, "cis"),
                    ],
                )
            cur_indo = await db.execute(
                """SELECT COUNT(*) AS c FROM products
                   WHERE game_id = ? AND subcategory = 'indonesia'""",
                (ff_id,),
            )
            indo_n = int((await cur_indo.fetchone())["c"])
            if indo_n == 0:
                await db.executemany(
                    """INSERT INTO products(
                        game_id, label, price_tjs, is_popular, is_best_value, is_active, sort_order, subcategory
                    ) VALUES(?,?,?,?,?,1,?,?)""",
                    [
                        (ff_id, "💎 100 Diamond", 12.00, 0, 0, 1, "indonesia"),
                        (ff_id, "💎 150 Diamond", 17.00, 0, 0, 2, "indonesia"),
                        (ff_id, "💎 210 Diamond", 22.00, 0, 0, 3, "indonesia"),
                        (ff_id, "💎 420 Diamond", 45.00, 0, 0, 4, "indonesia"),
                        (ff_id, "💎 500 Diamond", 55.00, 0, 0, 5, "indonesia"),
                        (ff_id, "💎 800 Diamond", 90.00, 0, 0, 6, "indonesia"),
                        (ff_id, "💎 1000 Diamond", 105.00, 0, 0, 7, "indonesia"),
                        (ff_id, "🗓️ Ваучери ҳафтагӣ", 25.00, 0, 0, 8, "indonesia"),
                        (ff_id, "🎫 Ваучери моҳона", 85.00, 0, 0, 9, "indonesia"),
                    ],
                )
        if pg_row:
            pg_id = int(pg_row["id"])
            cur_pg = await db.execute(
                "SELECT COUNT(*) AS c FROM products WHERE game_id = ?", (pg_id,)
            )
            if int((await cur_pg.fetchone())["c"]) == 0:
                await db.executemany(
                    """INSERT INTO products(
                        game_id, label, price_tjs, is_popular, is_best_value, is_active, sort_order, subcategory
                    ) VALUES(?,?,?,?,?,1,?,?)""",
                    [
                        (pg_id, "🎮 60 UC", 11.00, 0, 0, 1, "cis"),
                        (pg_id, "🎮 120 UC", 22.00, 0, 0, 2, "cis"),
                        (pg_id, "🎮 180 UC", 33.00, 1, 0, 3, "cis"),
                        (pg_id, "🎮 240 UC", 44.00, 0, 0, 4, "cis"),
                        (pg_id, "🎮 325 UC", 51.00, 0, 0, 5, "cis"),
                        (pg_id, "🎮 660 UC", 103.00, 0, 0, 6, "cis"),
                        (pg_id, "🎮 1800 UC", 283.00, 0, 0, 7, "cis"),
                        (pg_id, "🎮 3850 UC", 583.00, 0, 0, 8, "cis"),
                        (pg_id, "🎮 8100 UC", 1205.00, 0, 1, 9, "cis"),
                    ],
                )
        so_row = await (
            await db.execute(
                "SELECT id FROM games WHERE LOWER(TRIM(name)) IN ('standoff 2', 'standoff2') LIMIT 1"
            )
        ).fetchone()
        if not so_row:
            await db.execute(
                """INSERT INTO games(name, emoji, cover_path, is_active)
                   VALUES('Standoff 2','🎯',NULL,1)"""
            )
            await db.commit()
            so_row = await (
                await db.execute(
                    "SELECT id FROM games WHERE LOWER(name)='standoff 2' LIMIT 1"
                )
            ).fetchone()
        if so_row:
            so_id = int(so_row["id"])
            cur_so = await db.execute(
                "SELECT COUNT(*) AS c FROM products WHERE game_id = ?", (so_id,)
            )
            if int((await cur_so.fetchone())["c"]) == 0:
                await db.executemany(
                    """INSERT INTO products(
                        game_id, label, price_tjs, is_popular, is_best_value, is_active, sort_order, subcategory
                    ) VALUES(?,?,?,?,?,1,?,?)""",
                    [
                        (so_id, "🎯 100 золота", 19.0, 0, 0, 1, "cis"),
                        (so_id, "🎯 250 золота", 38.0, 0, 0, 2, "cis"),
                        (so_id, "🎯 500 золота", 72.0, 1, 0, 3, "cis"),
                        (so_id, "🎯 1000 золота", 132.0, 0, 0, 4, "cis"),
                        (so_id, "🎯 2500 золота", 330.0, 0, 0, 5, "cis"),
                        (so_id, "🎯 5000 золота", 660.0, 0, 1, 6, "cis"),
                        (so_id, "🏆 Gold Pass", 142.0, 1, 0, 7, "cis"),
                        (so_id, "🏆 Gold Pass +10 уровней", 185.0, 0, 0, 8, "cis"),
                    ],
                )
        await db.commit()
        from database.backup import backup_database

        backup_database()

# ✅ ГОТОВО: database/db.py
