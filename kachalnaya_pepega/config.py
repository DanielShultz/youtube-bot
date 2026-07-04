"""Конфигурация бота."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Настройки приложения."""

    bot_name: str
    bot_token: str
    allowed_user_ids: list[int]
    cookies_path: str
    media_base_path: str
    bot_data_path: str
    telegram_max_size: int
    compression_timeout: int
    telegram_upload_timeout: int
    telegram_connect_timeout: int
    telegram_pool_timeout: int
    default_video_type: str


def _parse_allowed_user_ids(value: str) -> list[int]:
    """Преобразует строку с id пользователей в список чисел."""
    return [int(item) for item in value.split(",") if item.strip()]


def _get_int_env(name: str, default: int) -> int:
    """Читает целочисленную настройку из окружения с fallback по умолчанию."""
    raw_value = os.getenv(name, str(default)).strip()
    try:
        return int(raw_value)
    except ValueError:
        return default


def load_settings() -> Settings:
    """Читает настройки из переменных окружения."""
    return Settings(
        bot_name="Качальная Пепега",
        bot_token=os.getenv("BOT_TOKEN", ""),
        allowed_user_ids=_parse_allowed_user_ids(os.getenv("ALLOWED_USER_IDS", "")),
        cookies_path="/app/cookies.txt",
        media_base_path="/media/music-videos",
        bot_data_path="/app/data",
        telegram_max_size=45 * 1024 * 1024,
        compression_timeout=300,
        telegram_upload_timeout=_get_int_env('TELEGRAM_UPLOAD_TIMEOUT', 600),
        telegram_connect_timeout=_get_int_env('TELEGRAM_CONNECT_TIMEOUT', 60),
        telegram_pool_timeout=_get_int_env('TELEGRAM_POOL_TIMEOUT', 60),
        default_video_type="Music Video",
    )


