"""Синхронные строки локализации без middleware (уведомления рефералам и т.п.)."""

import json
from pathlib import Path

_LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"
_RU: dict[str, str] | None = None
_TJ: dict[str, str] | None = None


def _bundle(lang: str) -> dict[str, str]:
    global _RU, _TJ
    if _RU is None:
        with (_LOCALES_DIR / "ru.json").open(encoding="utf-8") as f:
            _RU = json.load(f)
    if _TJ is None:
        with (_LOCALES_DIR / "tj.json").open(encoding="utf-8") as f:
            _TJ = json.load(f)
    return _TJ if lang == "tj" else _RU


def get_locale_string(lang: str, key: str, **kwargs: str | int) -> str:
    d = _bundle(lang if lang in ("ru", "tj") else "ru")
    text = d.get(key) or _bundle("ru").get(key, key)
    for k, v in kwargs.items():
        text = text.replace("{" + k + "}", str(v))
    return text

# ✅ ГОТОВО: utils/locale_text.py
