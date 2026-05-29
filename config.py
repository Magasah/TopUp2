from pathlib import Path
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    BOT_TOKEN: str
    ADMIN_IDS: str
    ADMIN_CHAT_ID: str = ""

    CHANNEL_ID: str
    CHANNEL_CHAT_ID: str = ""
    CHANNEL_USERNAME: str = ""
    REVIEWS_CHANNEL: str
    PUBLIC_CHANNEL: str = ""

    ADMIN_TG: str
    DC_CITY_NUMBER: str
    ALIF_NUMBER: str
    MASTERCARD_NUMBER: str
    MILLI_NUMBER: str = ""

    START_PHOTO_PATH: str = ""
    GAME_COVER_FF: str = ""
    GAME_COVER_PUBG: str = ""
    STORE_PHOTO_PATH: str = ""

    DATABASE_PATH: str = "./database/bot.db"

    # Мини-приложение «Подарки (NFT)» на Vercel — полный HTTPS URL (например https://xxx.vercel.app)
    GIFTS_WEBAPP_URL: str = "https://top-up-seven.vercel.app/"

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parent

    def resolve_optional_path(self, value: Optional[str]) -> Optional[str]:
        if value is None or not str(value).strip():
            return None
        p = Path(str(value).strip()).expanduser()
        resolved = p.resolve() if p.is_absolute() else (self.project_root / p).resolve()
        return str(resolved)

    @property
    def welcome_photo(self) -> str:
        p = self.resolve_optional_path(self.START_PHOTO_PATH or None)
        if p:
            return p
        fallback = self.project_root / "assets" / "welcome.jpg"
        return str(fallback)

    @property
    def store_photo(self) -> str:
        p = self.resolve_optional_path(self.STORE_PHOTO_PATH or None)
        if p:
            return p
        fallback = self.project_root / "assets" / "store.jpg"
        return str(fallback)

    def game_listing_cover(self, game_name: str, db_cover: Optional[str]) -> str:
        name = (game_name or "").lower()
        if "free fire" in name:
            env_p = self.resolve_optional_path(self.GAME_COVER_FF or None)
            if env_p:
                return env_p
        if "pubg" in name:
            env_p = self.resolve_optional_path(self.GAME_COVER_PUBG or None)
            if env_p:
                return env_p
        if db_cover:
            return db_cover
        return self.store_photo

    @property
    def channel_id_member_check(self) -> str:
        return (self.CHANNEL_CHAT_ID or self.CHANNEL_ID).strip()

    @property
    def announce_publish_target(self) -> str:
        """Чат для объявлений турниров и важных постов: -100… или @username (основа TopUp TJ)."""
        for raw in (self.CHANNEL_CHAT_ID, self.CHANNEL_ID, self.REVIEWS_CHANNEL):
            s = (raw or "").strip()
            if s:
                return s
        return ""

    @property
    def channel_subscribe_username(self) -> str:
        for raw in (self.CHANNEL_USERNAME, self.PUBLIC_CHANNEL):
            s = (raw or "").strip().lstrip("@")
            if s and not s.lstrip("-").isdigit():
                return s
        cid = (self.CHANNEL_ID or "").strip()
        if cid.startswith("@"):
            return cid.lstrip("@")
        return ""

    @property
    def admin_ids_list(self) -> List[int]:
        return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip()]

    @property
    def admin_chat_id_int(self) -> Optional[int]:
        s = (self.ADMIN_CHAT_ID or "").strip()
        if s.lstrip("-").isdigit():
            return int(s)
        return None

    def admin_contact_url(self) -> str:
        s = (self.ADMIN_TG or "").strip()
        if s.lstrip("-").isdigit():
            return f"tg://user?id={s}"
        return f"https://t.me/{s.lstrip('@')}"

    @property
    def gifts_webapp_url(self) -> str:
        return (self.GIFTS_WEBAPP_URL or "").strip()

    @field_validator("ADMIN_IDS")
    @classmethod
    def strip_admin_ids(cls, v: str) -> str:
        return v.strip()


config = Settings()
