CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    language TEXT DEFAULT 'ru',
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_active DATETIME
);

CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    emoji TEXT,
    cover_path TEXT,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER REFERENCES games(id),
    label TEXT NOT NULL,
    price_tjs REAL NOT NULL,
    is_popular INTEGER DEFAULT 0,
    is_best_value INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    subcategory TEXT DEFAULT 'cis'
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_tg_id INTEGER NOT NULL,
    username TEXT,
    game_name TEXT,
    product_label TEXT,
    price_tjs REAL,
    game_account_id TEXT,
    payment_method TEXT,
    receipt_file_id TEXT,
    status TEXT DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER REFERENCES orders(id),
    user_tg_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    channel_msg_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS broadcasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    sent_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Счётчики бота (например число вызовов /start), лёгкие UPDATE, без логов по каждому юзеру
CREATE TABLE IF NOT EXISTS bot_metrics (
    key TEXT PRIMARY KEY,
    value INTEGER NOT NULL DEFAULT 0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS referrals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER NOT NULL,
    referred_id INTEGER NOT NULL UNIQUE,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS standoff_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_tg_id INTEGER NOT NULL,
    username TEXT,
    product_label TEXT NOT NULL,
    price_tjs REAL NOT NULL,
    game_account_id TEXT,
    gold_amount INTEGER,
    is_manual INTEGER DEFAULT 0,
    payment_method TEXT,
    receipt_file_id TEXT,
    status TEXT DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

CREATE TABLE IF NOT EXISTS tournaments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    max_players INTEGER DEFAULT 100,
    status TEXT DEFAULT 'draft',
    room_id TEXT,
    room_password TEXT,
    channel_message_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    launched_at DATETIME
);

CREATE TABLE IF NOT EXISTS tournament_registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id),
    user_tg_id INTEGER NOT NULL,
    username TEXT,
    game_nickname TEXT,
    registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tournament_id, user_tg_id)
);

CREATE TABLE IF NOT EXISTS bonus_balance (
    user_tg_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS bonus_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_tg_id INTEGER NOT NULL,
    delta REAL NOT NULL,
    reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_tg_id INTEGER,
    username TEXT,
    order_type TEXT,
    phone_model TEXT,
    price_tjs REAL,
    payment_method TEXT,
    receipt_file_id TEXT,
    settings_text TEXT,
    vip_file_id TEXT,
    status TEXT DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

CREATE TABLE IF NOT EXISTS br_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_tg_id INTEGER,
    username TEXT,
    server_name TEXT,
    nickname TEXT,
    amount REAL,
    payment_method TEXT,
    receipt_file_id TEXT,
    status TEXT DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

CREATE TABLE IF NOT EXISTS steam_orders (
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
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS roulette_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_tg_id INTEGER,
    username TEXT,
    ticket_count INTEGER DEFAULT 0,
    price_tjs REAL DEFAULT 0,
    payment_method TEXT,
    receipt_file_id TEXT,
    status TEXT DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

CREATE TABLE IF NOT EXISTS required_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_ref TEXT NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admins (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    added_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
