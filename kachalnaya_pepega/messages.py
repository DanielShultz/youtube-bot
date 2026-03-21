"""Пользовательские сообщения бота."""

from .config import Settings
from .parsing import DownloadRequest


def build_start_message(settings: Settings) -> str:
    """Возвращает стартовое сообщение."""
    return (
        f"🎬 {settings.bot_name}\n\n"
        "Отправьте YouTube-ссылку для скачивания.\n"
        "Формат:\n"
        "URL [артист] [название] [тип]\n\n"
        "Пример:\n"
        'https://youtube.com/watch?v=... "Artist Name" "Song Title" "Music Video"\n\n'
        "После загрузки бот отправит оптимизированную версию для Telegram."
    )


def build_download_started_message(request: DownloadRequest) -> str:
    """Возвращает сообщение о начале загрузки."""
    return (
        "⏬ Начинаю загрузку...\n"
        f"Артист: {request.artist}\n"
        f"Название: {request.title}\n"
        f"Тип: {request.video_type}\n"
        "Качество оригинала: 1080p\n\n"
        "Это может занять несколько минут..."
    )


def build_original_ready_message(file_size: str) -> str:
    """Возвращает сообщение о завершении загрузки оригинала."""
    return f"✅ Оригинал загружен! ({file_size})\nОптимизирую для Telegram..."


def build_original_caption(request: DownloadRequest, file_size: str) -> str:
    """Возвращает подпись для оригинального видео."""
    return (
        "📹 Версия для Telegram (оригинал)\n"
        f"Артист: {request.artist}\n"
        f"Название: {request.title}\n"
        f"Тип: {request.video_type}\n"
        f"Размер: {file_size}\n\n"
        "📍 Оригинал сохранен на сервере"
    )


def build_compressed_caption(request: DownloadRequest, original_size: int, compressed_size: int) -> str:
    """Возвращает подпись для сжатого видео."""
    caption = (
        "📹 Версия для Telegram\n"
        f"Артист: {request.artist}\n"
        f"Название: {request.title}\n"
        f"Тип: {request.video_type}\n"
        f"Размер: {format_file_size(compressed_size)}\n"
    )
    if compressed_size < original_size:
        caption += f"Сжатие: {(compressed_size / original_size) * 100:.1f}% от оригинала\n"
    return caption + "\n📍 Оригинал сохранен на сервере"


def build_timeout_message(relative_path: str, file_size: str) -> str:
    """Возвращает сообщение о таймауте сжатия."""
    return (
        "⏰ Таймаут сжатия\n"
        f"Оригинал сохранен: {relative_path}\n"
        f"Размер: {file_size}\n\n"
        "Попробуйте более короткое видео или другой формат."
    )


def build_compression_failed_message(relative_path: str, file_size: str) -> str:
    """Возвращает сообщение о проблеме при подготовке версии для Telegram."""
    return (
        "⚠️ Оригинал загружен, но не удалось создать версию для Telegram.\n"
        f"Файл сохранен: {relative_path}\n"
        f"Размер: {file_size}"
    )


def format_file_size(size_bytes: int) -> str:
    """Форматирует размер файла."""
    if size_bytes <= 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"