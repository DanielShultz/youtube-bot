"""Конфигурация бота."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    """Настройки приложения."""

    bot_name: str
    bot_token: str
    allowed_users: list[int]
    cookies_path: str
    media_base_path: str
    telegram_max_size: int
    compression_timeout: int
    default_video_type: str


def _parse_allowed_users(value: str) -> list[int]:
    """Преобразует строку с id пользователей в список чисел."""
    return [int(item) for item in value.split(",") if item.strip()]


def load_settings() -> Settings:
    """Читает настройки из переменных окружения."""
    return Settings(
        bot_name="Качальная Пепега",
        bot_token=os.getenv("BOT_TOKEN", ""),
        allowed_users=_parse_allowed_users(os.getenv("ALLOWED_USER_IDS", "")),
        cookies_path="/app/cookies.txt",
        media_base_path="/media/music-videos",
        telegram_max_size=45 * 1024 * 1024,
        compression_timeout=300,
        default_video_type="Music Video",
    )