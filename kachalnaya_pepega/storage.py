"""Работа с путями и именами файлов."""

import os
from dataclasses import dataclass

INVALID_FILENAME_CHARS = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']


@dataclass(frozen=True)
class MediaPaths:
    """Пути для сохранения оригинала и версии для Telegram."""

    full_path: str
    relative_path: str
    safe_genre: str
    safe_artist: str
    safe_title: str
    safe_type: str
    filename: str
    expected_original_file: str
    compressed_file: str


def sanitize_component(name: str) -> str:
    """Подготавливает безопасное имя папки или файла."""
    result = name or 'Unknown'
    for char in INVALID_FILENAME_CHARS:
        result = result.replace(char, '_')
    return result.strip()


def build_media_paths(base_path: str, genre: str, artist: str, title: str, video_type: str) -> MediaPaths:
    """Создаёт структуру путей для сохранения видео."""
    safe_genre = sanitize_component(genre)
    safe_artist = sanitize_component(artist)
    safe_title = sanitize_component(title)
    safe_type = sanitize_component(video_type)
    full_path = os.path.join(base_path, safe_genre, safe_artist, safe_title)
    os.makedirs(full_path, exist_ok=True)
    filename = f'{safe_artist} - {safe_title} - {safe_type}'
    return MediaPaths(
        full_path=full_path,
        relative_path=f'{safe_genre}/{safe_artist}/{safe_title}',
        safe_genre=safe_genre,
        safe_artist=safe_artist,
        safe_title=safe_title,
        safe_type=safe_type,
        filename=filename,
        expected_original_file=os.path.join(full_path, f'{filename}.mp4'),
        compressed_file=os.path.join(full_path, f'{filename}_telegram.mp4'),
    )
