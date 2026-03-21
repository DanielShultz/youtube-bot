"""Парсинг пользовательского ввода."""

from dataclasses import dataclass
import logging
import shlex


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


def _is_youtube_url(url: str) -> bool:
    """Проверяет, что ссылка относится к YouTube."""
    return "youtube.com" in url or "youtu.be" in url


def parse_user_input(text: str, default_video_type: str) -> DownloadRequest | None:
    """Преобразует текст пользователя в структуру запроса."""
    if not text or not text.strip():
        return None
    parts = _parse_parts(text)
    if not parts or not _is_youtube_url(parts[0]):
        return None
    artist = parts[1] if len(parts) > 1 else "Various"
    title = parts[2] if len(parts) > 2 else "Unknown"
    video_type = " ".join(parts[3:]) if len(parts) > 3 else default_video_type
    return DownloadRequest(
        url=parts[0],
        artist=artist.strip("\"'"),
        title=title.strip("\"'"),
        video_type=video_type.strip("\"'"),
    )