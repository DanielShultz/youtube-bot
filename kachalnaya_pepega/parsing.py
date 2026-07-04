"""Парсинг пользовательского ввода."""

import logging
import shlex
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DownloadRequest:
    """Данные запроса на загрузку."""

    url: str
    artist: str
    title: str
    video_type: str


def _parse_parts(text: str) -> list[str]:
    """Разбивает строку на части с поддержкой кавычек."""
    try:
        return shlex.split(text.strip())
    except ValueError as error:
        logger.warning("Не удалось распарсить ввод через shlex: %s", error)
        return text.strip().split()


def is_youtube_url(url: str) -> bool:
    """Проверяет, что ссылка относится к YouTube."""
    return "youtube.com" in url or "youtu.be" in url


def normalize_youtube_url(url: str) -> str:
    """Оставляет только video id и убирает playlist/query-шум."""
    clean_url = url.strip()
    parsed = urlparse(clean_url)
    host = parsed.netloc.lower()

    if "youtu.be" in host:
        video_id = parsed.path.strip("/").split("/")[0]
        return f"https://youtu.be/{video_id}" if video_id else clean_url

    if "youtube.com" not in host:
        return clean_url

    video_id = parse_qs(parsed.query).get("v", [""])[0].strip()
    if video_id:
        return f"https://youtu.be/{video_id}"
    return clean_url


def parse_user_input(text: str, default_video_type: str) -> DownloadRequest | None:
    """Преобразует текст пользователя в структуру запроса."""
    if not text or not text.strip():
        return None

    parts = _parse_parts(text)
    if not parts or not is_youtube_url(parts[0]):
        return None

    artist = parts[1] if len(parts) > 1 else "Various"
    title = parts[2] if len(parts) > 2 else "Unknown"
    video_type = " ".join(parts[3:]) if len(parts) > 3 else default_video_type

    return DownloadRequest(
        url=normalize_youtube_url(parts[0]),
        artist=artist.strip("\"'"),
        title=title.strip("\"'"),
        video_type=video_type.strip("\"'"),
    )
