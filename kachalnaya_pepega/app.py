"""Основная логика Telegram-бота."""

import asyncio
import logging
import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from .compressor import VideoCompressor
from .config import Settings
from .diagnostics import collect_status_lines
from .downloader import YouTubeDownloader
from .messages import (
    build_compressed_caption,
    build_compression_failed_message,
    build_download_started_message,
    build_original_caption,
    build_original_ready_message,
    build_start_message,
    build_timeout_message,
    format_file_size,
)
from .parsing import DownloadRequest, parse_user_input
from .storage import MediaPaths, build_media_paths


logger = logging.getLogger(__name__)


class KachalnayaPepegaBot:
    """Telegram-бот для загрузки видео."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.application: Application | None = None
        self.downloader = YouTubeDownloader(settings.cookies_path)
        self.compressor = VideoCompressor(settings.telegram_max_size)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Отправляет стартовую инструкцию."""
        if not await self._is_authorized(update):
            return
        await update.message.reply_text(build_start_message(self.settings))

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Отправляет текущий статус сервиса."""
        if not await self._is_authorized(update):
            return
        await update.message.reply_text("\n".join(collect_status_lines(self.settings)))

    async def handle_download(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обрабатывает сообщение с ссылкой."""
        if not await self._is_authorized(update):
            return
        request = parse_user_input(update.message.text.strip(), self.settings.default_video_type)
        if not request:
            await update.message.reply_text(self._invalid_format_message())
            return
        media_paths = build_media_paths(
            self.settings.media_base_path,
            request.artist,
            request.title,
            request.video_type,
        )
        await update.message.reply_text(build_download_started_message(request))
        await self._process_download(update, request, media_paths)

    async def _process_download(
        self,
        update: Update,
        request: DownloadRequest,
        media_paths: MediaPaths,
    ) -> None:
        """Выполняет полную обработку загрузки."""
        try:
            result = self.downloader.download(request.url, os.path.join(media_paths.full_path, media_paths.filename))
            if not result["success"]:
                await update.message.reply_text(f"❌ Ошибка загрузки: {str(result['message'])[:500]}")
                return
            original_file = str(result["file_path"])
            await self._handle_downloaded_file(update, request, media_paths, original_file)
        except Exception as error:
            logger.exception("Ошибка обработки загрузки")
            await update.message.reply_text(f"❌ Ошибка: {str(error)[:500]}")
        finally:
            self._remove_file(media_paths.compressed_file)

    async def _handle_downloaded_file(
        self,
        update: Update,
        request: DownloadRequest,
        media_paths: MediaPaths,
        original_file: str,
    ) -> None:
        """Выбирает сценарий отправки после загрузки оригинала."""
        original_size = os.path.getsize(original_file)
        await update.message.reply_text(build_original_ready_message(format_file_size(original_size)))
        if original_size <= self.settings.telegram_max_size:
            await self._send_original_video(update, request, original_file, original_size)
            return
        await self._send_compressed_video(update, request, media_paths, original_file, original_size)

    async def _send_original_video(
        self,
        update: Update,
        request: DownloadRequest,
        original_file: str,
        original_size: int,
    ) -> None:
        """Отправляет файл без дополнительного сжатия."""
        with open(original_file, "rb") as video_file:
            await update.message.reply_video(
                video=video_file,
                caption=build_original_caption(request, format_file_size(original_size)),
                supports_streaming=True,
            )
        await update.message.reply_text("✅ Файл отправлен без сжатия.")

    async def _send_compressed_video(
        self,
        update: Update,
        request: DownloadRequest,
        media_paths: MediaPaths,
        original_file: str,
        original_size: int,
    ) -> None:
        """Сжимает файл и отправляет его в Telegram."""
        try:
            compressed = await asyncio.wait_for(
                self._compress_in_executor(original_file, media_paths.compressed_file),
                timeout=self.settings.compression_timeout,
            )
            if not compressed or not os.path.exists(media_paths.compressed_file):
                await update.message.reply_text(
                    build_compression_failed_message(media_paths.relative_path, format_file_size(original_size))
                )
                return
            await self._reply_with_compressed_video(update, request, media_paths, original_size)
        except asyncio.TimeoutError:
            await update.message.reply_text(
                build_timeout_message(media_paths.relative_path, format_file_size(original_size))
            )

    async def _reply_with_compressed_video(
        self,
        update: Update,
        request: DownloadRequest,
        media_paths: MediaPaths,
        original_size: int,
    ) -> None:
        """Отправляет сжатый файл и удаляет временную копию."""
        compressed_size = os.path.getsize(media_paths.compressed_file)
        with open(media_paths.compressed_file, "rb") as video_file:
            await update.message.reply_video(
                video=video_file,
                caption=build_compressed_caption(request, original_size, compressed_size),
                supports_streaming=True,
                write_timeout=60,
            )
        self._remove_file(media_paths.compressed_file)
        await update.message.reply_text("🧹 Временный файл удален.")

    async def _compress_in_executor(self, original_file: str, compressed_file: str) -> bool:
        """Запускает сжатие в отдельном потоке."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.compressor.compress, original_file, compressed_file)

    async def _is_authorized(self, update: Update) -> bool:
        """Проверяет доступ пользователя."""
        user_id = update.effective_user.id
        if user_id in self.settings.allowed_users:
            return True
        await update.message.reply_text("❌ Доступ запрещен")
        logger.warning("Неавторизованный доступ от пользователя %s", user_id)
        return False

    def run(self) -> None:
        """Запускает polling бота."""
        if not self.settings.bot_token:
            raise RuntimeError("BOT_TOKEN не установлен в переменных окружения")
        self.application = Application.builder().token(self.settings.bot_token).build()
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("status", self.status))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_download))
        self.application.run_polling(allowed_updates=Update.ALL_TYPES, poll_interval=1.0, timeout=30)

    @staticmethod
    def _invalid_format_message() -> str:
        """Возвращает текст ошибки формата ввода."""
        return '❌ Неверный формат.\nПример:\nhttps://youtube.com/... "Артист" "Название" "Тип"'

    @staticmethod
    def _remove_file(path: str) -> None:
        """Удаляет временный файл, если он существует."""
        if os.path.exists(path):
            os.remove(path)