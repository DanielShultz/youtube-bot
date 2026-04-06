"""Диагностика зависимостей сервиса."""

from dataclasses import dataclass
import os
import subprocess

from .config import Settings


@dataclass(frozen=True)
class DependencyStatus:
    """Результат проверки внешней зависимости."""

    name: str
    status: str


def _read_command_output(command: list[str], timeout: int) -> str:
    """Возвращает первую полезную строку вывода команды."""
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        return "не доступен"
    output = result.stdout.strip().splitlines()
    return output[0] if output else "доступен"


def collect_status_lines(settings: Settings) -> list[str]:
    """Собирает строки для команды статуса."""
    dependencies = [
        DependencyStatus("yt-dlp", _read_command_output(["yt-dlp", "--version"], 5)),
        DependencyStatus("ffmpeg", _read_command_output(["ffmpeg", "-version"], 5)),
        DependencyStatus("deno", _read_command_output(["deno", "--version"], 5)),
    ]
    lines = ["🤖 Бот работает", ""]
    lines.extend([f"✅ {item.name}: {item.status}" for item in dependencies])
    cookies_status = "найдены" if os.path.exists(settings.cookies_path) else "не найдены"
    lines.extend(
        [
            f"🔐 cookies: {cookies_status}",
            "",
            f"📁 Папка для медиа: {settings.media_base_path}",
            f"📏 Лимит Telegram: {settings.telegram_max_size // (1024 * 1024)}MB",
            f"⏱️ Таймаут сжатия: {settings.compression_timeout // 60} минут",
            "",
            "Команды:",
            "/start - инструкция",
            "/status - проверка системы",
        ]
    )
    return lines
