"""Загрузка видео через yt-dlp."""

import logging
import os
import subprocess

from .parsing import is_youtube_url


logger = logging.getLogger(__name__)


class YouTubeDownloader:
    """Сервис загрузки видео с YouTube."""

    def __init__(self, cookies_path: str) -> None:
        self.cookies_path = cookies_path

    def download(self, url: str, output_path: str) -> dict[str, str | bool | None]:
        """Загружает видео и возвращает путь к файлу."""
        if not is_youtube_url(url):
            return self._failure("Неверный YouTube URL")
        command = self._build_command(url, output_path)
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                return self._failure(self._extract_error(result))
            file_path = self._find_downloaded_file(output_path)
            if not file_path:
                return self._failure("Файл не найден после загрузки")
            return {"success": True, "file_path": file_path, "message": "Загрузка успешна"}
        except subprocess.TimeoutExpired:
            return self._failure("Таймаут загрузки (5 минут)")
        except Exception as error:
            logger.exception("Ошибка при загрузке видео")
            return self._failure(f"Исключение: {str(error)[:200]}")

    def _build_command(self, url: str, output_path: str) -> list[str]:
        """Собирает команду запуска yt-dlp."""
        command = [
            "yt-dlp",
            "-o", f"{output_path}.%(ext)s",
            "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
            "--write-thumbnail",
            "--convert-thumbnails", "jpg",
            "--ffmpeg-location", "/usr/bin",
            "--js-runtimes", "deno",
            "--remote-components", "ejs:github",
            "--no-cookies",
            "--retries", "2",
            "--fragment-retries", "2",
            "--socket-timeout", "30",
            "--source-address", "0.0.0.0",
            "--ignore-errors",
        ]
        if os.path.exists(self.cookies_path):
            command.extend(["--cookies", self.cookies_path])
        return command + [url]

    def _find_downloaded_file(self, base_path: str) -> str | None:
        """Ищет скачанный файл рядом с ожидаемым путём."""
        for ext in [".mp4", ".mkv", ".webm"]:
            possible_file = base_path + ext
            if os.path.exists(possible_file):
                return possible_file
        directory = os.path.dirname(base_path)
        for file_name in os.listdir(directory):
            if file_name.endswith((".mp4", ".mkv", ".webm")):
                return os.path.join(directory, file_name)
        return None

    @staticmethod
    def _extract_error(result: subprocess.CompletedProcess[str]) -> str:
        """Возвращает короткое сообщение об ошибке yt-dlp."""
        error = result.stderr[-500:] if result.stderr else result.stdout[-500:]
        return f"Ошибка yt-dlp: {error or 'Неизвестная ошибка'}"

    @staticmethod
    def _failure(message: str) -> dict[str, str | bool | None]:
        """Формирует единый ответ об ошибке."""
        return {"success": False, "file_path": None, "message": message}