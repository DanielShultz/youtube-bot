"""Подготовка видео под лимиты Telegram."""

import logging
import os
import shutil
import subprocess


logger = logging.getLogger(__name__)


class VideoCompressor:
    """Сервис сжатия видео."""

    def __init__(self, max_size: int) -> None:
        self.max_size = max_size

    def compress(self, input_path: str, output_path: str) -> bool:
        """Готовит файл для отправки в Telegram."""
        if not os.path.exists(input_path):
            logger.error("Входной файл не существует: %s", input_path)
            return False
        video_info = self._get_video_info(input_path)
        if video_info["file_size"] <= self.max_size:
            return self._copy_file(input_path, output_path)
        settings = self._calculate_settings(video_info)
        success = self._compress_video(input_path, output_path, settings, 300)
        if not success or not os.path.exists(output_path):
            return False
        if os.path.getsize(output_path) <= self.max_size * 1.1:
            return True
        return self._compress_video(input_path, output_path, self._aggressive_settings(), 180)

    def _get_video_info(self, input_path: str) -> dict[str, int | float]:
        """Читает базовые свойства видео через ffprobe."""
        return {
            "height": self._read_probe_value(input_path, "stream=height", 1080),
            "duration": self._read_probe_value(input_path, "format=duration", 180.0),
            "file_size": os.path.getsize(input_path),
        }

    def _read_probe_value(self, input_path: str, field: str, fallback: int | float) -> int | float:
        """Возвращает одно значение ffprobe или fallback."""
        command = [
            "ffprobe", "-v", "error", "-show_entries", field,
            "-of", "default=noprint_wrappers=1:nokey=1", input_path,
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            if result.returncode != 0 or not result.stdout.strip():
                return fallback
            return type(fallback)(result.stdout.strip())
        except Exception:
            return fallback

    def _calculate_settings(self, video_info: dict[str, int | float]) -> dict[str, str | int]:
        """Подбирает обычные параметры сжатия."""
        ratio = self.max_size / int(video_info["file_size"])
        if ratio > 0.7:
            return {"scale_height": min(720, int(video_info["height"])), "crf": 24, "preset": "fast", "audio_bitrate": "64k"}
        if ratio > 0.4:
            return {"scale_height": min(480, int(video_info["height"])), "crf": 26, "preset": "faster", "audio_bitrate": "64k"}
        if ratio > 0.2:
            return {"scale_height": min(360, int(video_info["height"])), "crf": 28, "preset": "veryfast", "audio_bitrate": "64k"}
        return {"scale_height": min(240, int(video_info["height"])), "crf": 30, "preset": "ultrafast", "audio_bitrate": "64k"}

    def _aggressive_settings(self) -> dict[str, str | int]:
        """Возвращает параметры агрессивного сжатия."""
        return {"scale_height": 480, "crf": 32, "preset": "ultrafast", "audio_bitrate": "48k"}

    def _compress_video(
        self,
        input_path: str,
        output_path: str,
        settings: dict[str, str | int],
        timeout: int,
    ) -> bool:
        """Запускает ffmpeg с заданными параметрами."""
        command = [
            "ffmpeg", "-i", input_path, "-c:v", "libx264", "-crf", str(settings["crf"]),
            "-preset", str(settings["preset"]), "-vf", f"scale=-2:{settings['scale_height']}",
            "-c:a", "aac", "-b:a", str(settings["audio_bitrate"]), "-movflags", "+faststart",
            "-threads", "1", "-y", output_path,
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def _copy_file(input_path: str, output_path: str) -> bool:
        """Копирует файл без изменений."""
        try:
            shutil.copy2(input_path, output_path)
            return True
        except Exception:
            return False
