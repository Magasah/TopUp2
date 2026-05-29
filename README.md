# TopUp Bot

Telegram-бот на **aiogram 3** для пополнения игр и сервисов (Standoff 2, Steam, Black Russia, Telegram Stars / Premium и др.) с SQLite и админ-панелью.

## Требования

- **Python 3.11+** (рекомендуется 3.11, как в `requirements.txt`)
- Linux или Windows Server

## Локальный запуск

```bash
git clone https://github.com/Magasah/TopUp-Bot.git
cd TopUp-Bot
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Отредактируйте .env: BOT_TOKEN, ADMIN_IDS, каналы и реквизиты

python bot.py
```

Файл `.env` в репозиторий не попадает (см. `.gitignore`).

## Меню команд в Telegram

У всех пользователей в личке доступна кнопка **«Меню»** (слева от поля ввода) с командами:

- `/start` — главное меню
- `/settings` — язык и реферальная программа

У администраторов дополнительно: `/admin`, `/stats`.

## Сохранность данных при перезапуске

Заказы, товары, пользователи и статистика (`/start`, выручка и т.д.) хранятся в **SQLite** (`DATABASE_PATH`, по умолчанию `database/bot.db`).

- При обновлении кода **не удаляйте** файл `bot.db`.
- При каждом старте бота создаётся резервная копия в `database/backups/` (хранятся последние 10).
- Каталог товаров **не перезаписывается** при рестарте, если товары уже есть в БД.

## Картинки в `public/`

Шаблоны подхватываются автоматически (`utils/assets.py`). Имеет смысл положить в `public/`:

| Раздел | Предпочтительные имена файлов |
|--------|-------------------------------|
| Меню Telegram | `telegram.png`, затем `Telegram.jpg` |
| Stars | `telegram_stars.png` |
| Premium | `telegram_premium.png` |
| Standoff 2 | `standoff2.jpg`, `Стендоф голда.jpg` и т.п. |

## Деплой на сервер (Linux, systemd)

1. На сервере установите Python 3.11 и git.
2. Клонируйте репозиторий в каталог, например `/opt/topup-bot`:

   ```bash
   sudo mkdir -p /opt/topup-bot
   sudo chown $USER:$USER /opt/topup-bot
   git clone https://github.com/Magasah/TopUp-Bot.git /opt/topup-bot
   cd /opt/topup-bot
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Создайте `.env` из примера и заполните переменные (токен бота, админы, каналы).

4. Юнит **systemd** `/etc/systemd/system/topup-bot.service`:

   ```ini
   [Unit]
   Description=TopUp Telegram Bot
   After=network.target

   [Service]
   Type=simple
   User=YOUR_USER
   WorkingDirectory=/opt/topup-bot
   Environment=PATH=/opt/topup-bot/.venv/bin:/usr/bin
   ExecStart=/opt/topup-bot/.venv/bin/python bot.py
   Restart=on-failure
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```

5. Запуск и автозагрузка:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now topup-bot
   sudo journalctl -u topup-bot -f
   ```

## Обновление на сервере

```bash
cd /opt/topup-bot
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart topup-bot
```

Репозиторий: [https://github.com/Magasah/TopUp-Bot](https://github.com/Magasah/TopUp-Bot.git)
