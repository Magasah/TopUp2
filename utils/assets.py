import os
import re

from aiogram.types import FSInputFile

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
PUBLIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")

# Имена файлов (любой регистр). Дополнительно см. _public_keyword_match ниже.
GAME_PHOTOS = {
    "steam": ["Steam.jpg", "steam.jpg", "steam.png"],
    "black_russia": ["black_russia.jpg", "blackrussia.jpg", "br.jpg", "black russia.jpg"],
    "free_fire": ["free_fire.jpg", "freefire.jpg", "ff.jpg", "free fire.jpg"],
    "pubg": ["pubg.jpg", "pubg_mobile.jpg", "pubg mobile.jpg"],
    "standoff2": [
        "standoff2.jpg",
        "standoff.jpg",
        "standoff_2.jpg",
        "стендоф голда.jpg",
        "стендоф.jpg",
    ],
    # Сначала логотип/шаблон Telegram, не telegram.jpg (часто ошибочная копия другой игры).
    "telegram": [
        "telegram.png",
        "Telegram.jpg",
        "Telegram.png",
        "telegram.jpg",
    ],
    "telegram_premium": [
        "telegram_premium.png",
        "telegram_premium.jpg",
        "telegrampremium.jpg",
        "telegram premium.jpg",
        "premium.jpg",
    ],
    "telegram_stars": [
        "telegram_stars.png",
        "telegram_stars.jpg",
        "telegramstars.jpg",
        "telegram stars.jpg",
        "Telegram Stars.jpg",
        "stars.jpg",
    ],
    "telegram_bot_order": ["telegram_bot.jpg", "telegrambot.jpg", "bot_order.jpg", "telegram_order.jpg"],
    "welcome": ["welcome.jpg", "welcome.png"],
    "chat_gpt": ["chat_gpt.jpg", "chatgpt.jpg", "chat_gpt.png", "ChatGPT.jpg"],
    "claude": ["claude.jpg", "claude.png", "Claude.jpg"],
    "gemini": ["gemini.jpg", "gemini.png", "Gemini.jpg"],
    "grok": ["grok.jpg", "grok.png", "Grok.jpg"],
    "cursor": ["cursor.jpg", "cursor.png", "Cursor.jpg"],
    "github_copilot": [
        "githubcopilot.jpg",
        "github_copilot.jpg",
        "copilot.jpg",
        "GitHub Copilot.jpg",
    ],
    "midjourney": ["midjourney.jpg", "midjourney.png", "Midjourney.jpg"],
    "runway": ["runway.jpg", "runway.png", "Runway.jpg"],
    "kling": ["kling.jpg", "kling.png", "kling_ai.jpg", "Kling.jpg"],
    "suno": ["suno.jpg", "suno.png", "Suno.jpg"],
    "elevenlabs": ["elevenlabs.jpg", "elevenlabs.png", "ElevenLabs.jpg"],
    "perplexity": [
        "perprexity.jpg",
        "perplexity.jpg",
        "perplexity.png",
        "Perplexity.jpg",
    ],
}

# Ключевые слова для поиска логотипов ИИ в public/ (если имя файла отличается)
_AI_PHOTO_KEYWORDS: dict[str, tuple[str, ...]] = {
    "chat_gpt": ("chatgpt", "chat_gpt", "chat gpt", "openai"),
    "claude": ("claude", "anthropic"),
    "gemini": ("gemini", "google gemini"),
    "grok": ("grok", "xai"),
    "cursor": ("cursor", "anysphere"),
    "github_copilot": ("copilot", "github"),
    "midjourney": ("midjourney",),
    "runway": ("runway",),
    "kling": ("kling",),
    "suno": ("suno",),
    "elevenlabs": ("elevenlabs", "eleven labs"),
    "perplexity": ("perplexity", "perprexity"),
}


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def _list_public_files() -> list[str]:
    if not os.path.isdir(PUBLIC_DIR):
        return []
    try:
        return [f for f in os.listdir(PUBLIC_DIR) if not f.startswith(".")]
    except Exception:
        return []


def _public_keyword_match(game_key: str) -> str | None:
    """Подобрать картинку из public/ по ключевым словам (пробелы, кириллица)."""
    files = _list_public_files()
    if not files:
        return None

    def pick(predicate) -> str | None:
        # длиннее имя — обычно конкретнее (Telegram Premium vs Telegram)
        for orig in sorted(files, key=lambda x: len(x), reverse=True):
            n = _norm(orig)
            if not n.endswith((".jpg", ".jpeg", ".png", ".webp")):
                continue
            if predicate(n, orig):
                return orig
        return None

    if game_key == "standoff2":

        def p(n: str, _o: str) -> bool:
            if "telegram" in n or "телеграм" in n:
                return False
            if any(k in n for k in ("standoff", "стендоф", "stendof")):
                return True
            # «голд»/«золот» только вместе со стендофом в имени
            if any(k in n for k in ("голд", "золот", "золота")):
                return any(k in n for k in ("standoff", "стендоф", "stendof"))
            return False

        hit = pick(p)
        if hit:
            return hit

    if game_key == "telegram_stars":

        def p2(n: str, _o: str) -> bool:
            return ("star" in n or "звезд" in n or "stars" in n) and (
                "telegram" in n or "телеграм" in n
            )

        hit = pick(p2)
        if hit:
            return hit

    if game_key == "telegram_premium":

        def p3(n: str, _o: str) -> bool:
            return ("premium" in n or "премиум" in n) and (
                "telegram" in n or "телеграм" in n or "tg" in n
            )

        hit = pick(p3)
        if hit:
            return hit

    if game_key == "telegram":

        def p4(n: str, _o: str) -> bool:
            if "star" in n or "звезд" in n:
                return False
            if "premium" in n or "премиум" in n:
                return False
            if "bot" in n or "бот" in n or "order" in n:
                return False
            return "telegram" in n or "телеграм" in n

        hit = pick(p4)
        if hit:
            return hit

    return None


def _find_in_folder_by_priority(folder: str, preferred_original_names: list[str]) -> str | None:
    """Первый существующий файл из списка (порядок = приоритет), сравнение имён без учёта регистра."""
    if not os.path.isdir(folder):
        return None
    try:
        entries = os.listdir(folder)
    except Exception:
        return None
    by_norm = {_norm(e): e for e in entries}
    for orig in preferred_original_names:
        got = by_norm.get(_norm(orig))
        if got:
            path = os.path.join(folder, got)
            if os.path.exists(path):
                return got
    return None


def _ai_keyword_match(photo_key: str) -> str | None:
    keywords = _AI_PHOTO_KEYWORDS.get(photo_key)
    if not keywords:
        return None
    files = _list_public_files()
    if not files:
        return None

    def pick(predicate) -> str | None:
        for orig in sorted(files, key=lambda x: len(x), reverse=True):
            n = _norm(orig)
            if not n.endswith((".jpg", ".jpeg", ".png", ".webp")):
                continue
            if predicate(n):
                return orig
        return None

    def p(n: str) -> bool:
        return any(k in n for k in keywords)

    return pick(p)


def get_ai_photo(photo_key: str) -> FSInputFile | None:
    """Фото ИИ-сервиса из public/ (или assets/) по photo_key (например chat_gpt, claude)."""
    preferred = GAME_PHOTOS.get(photo_key, [])
    for folder in (PUBLIC_DIR, ASSETS_DIR):
        original_name = _find_in_folder_by_priority(folder, preferred)
        if original_name:
            path = os.path.join(folder, original_name)
            return FSInputFile(path)

    kw = _ai_keyword_match(photo_key)
    if kw:
        path = os.path.join(PUBLIC_DIR, kw)
        if os.path.exists(path):
            return FSInputFile(path)
    return None


def get_game_photo(game_key: str) -> FSInputFile | None:
    """Найти фото: сначала точные имена в assets/ и public/ (порядок в GAME_PHOTOS), затем эвристика по public/."""
    preferred = GAME_PHOTOS.get(game_key, [])
    # Сначала public — шаблоны проекта; потом assets (дефолты).
    for folder in (PUBLIC_DIR, ASSETS_DIR):
        original_name = _find_in_folder_by_priority(folder, preferred)
        if original_name:
            path = os.path.join(folder, original_name)
            return FSInputFile(path)

    kw = _public_keyword_match(game_key)
    if kw:
        path = os.path.join(PUBLIC_DIR, kw)
        if os.path.exists(path):
            return FSInputFile(path)
    return None
