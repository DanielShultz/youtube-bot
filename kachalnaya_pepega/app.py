"""Основная логика Telegram-бота."""

import asyncio
from dataclasses import asdict, replace
import logging
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TimedOut
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from .compressor import VideoCompressor
from .config import Settings
from .diagnostics import collect_status_lines
from .downloader import YouTubeDownloader
from .genre_catalog import GenreCatalog
from .messages import (
    build_compressed_caption,
    build_compression_failed_message,
    build_download_started_message,
    build_original_caption,
    build_original_ready_message,
    build_start_message,
    build_timeout_message,
    build_upload_timeout_message,
    format_file_size,
)
from .parsing import DownloadRequest, parse_user_input
from .storage import MediaPaths, build_media_paths


logger = logging.getLogger(__name__)
PENDING_REQUEST_KEY = 'pending_download_request'


class KachalnayaPepegaBot:
    """Telegram-бот для загрузки видео."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.application: Application | None = None
        self.downloader = YouTubeDownloader(settings.cookies_path)
        self.compressor = VideoCompressor(settings.telegram_max_size)
        self.genre_catalog = GenreCatalog(settings.bot_data_path)
        self._background_tasks: set[asyncio.Task] = set()

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
        """Обрабатывает сообщение со ссылкой."""
        if not await self._is_authorized(update):
            return
        request = parse_user_input(update.message.text.strip(), self.settings.default_video_type)
        if not request:
            await update.message.reply_text(self._invalid_format_message())
            return
        canonical_request = self._with_canonical_artist(request)
        genre = self.genre_catalog.resolve(canonical_request.artist)
        if not genre:
            context.user_data[PENDING_REQUEST_KEY] = asdict(canonical_request)
            await update.message.reply_text(
                f'Не знаю жанр для артиста {canonical_request.artist}. Выберите папку:',
                reply_markup=self._genre_keyboard(),
            )
            return
        await self._start_download(update.message, canonical_request, genre)

    async def handle_genre_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Принимает выбранный жанр для нового артиста."""
        if not await self._is_authorized(update):
            return
        query = update.callback_query
        await query.answer()
        if query.data == 'genre:cancel':
            context.user_data.pop(PENDING_REQUEST_KEY, None)
            await query.edit_message_text('Выбор жанра отменён.')
            return
        pending_data = context.user_data.get(PENDING_REQUEST_KEY)
        if not pending_data:
            await query.edit_message_text('Запрос уже потерян. Отправьте ссылку заново.')
            return
        genre = self._genre_from_callback(query.data)
        if not genre:
            await query.edit_message_text('Не удалось распознать жанр. Отправьте ссылку заново.')
            return
        request = DownloadRequest(**pending_data)
        canonical_artist = self.genre_catalog.assign(request.artist, genre)
        canonical_request = replace(request, artist=canonical_artist)
        context.user_data.pop(PENDING_REQUEST_KEY, None)
        await query.edit_message_text(f'Жанр сохранён: {genre}')
        await self._start_download(query.message, canonical_request, genre)

    async def _start_download(self, message, request: DownloadRequest, genre: str) -> None:
        """Запускает обычную загрузку в уже известную жанровую папку."""
        media_paths = build_media_paths(
            self.settings.media_base_path,
            genre,
            request.artist,
            request.title,
            request.video_type,
        )
        await message.reply_text(build_download_started_message(request, genre))
        await self._process_download(message, request, media_paths)

    async def _process_download(self, message, request: DownloadRequest, media_paths: MediaPaths) -> None:
        """Выполняет полную обработку загрузки."""
        try:
            result = self.downloader.download(request.url, os.path.join(media_paths.full_path, media_paths.filename))
            if not result['success']:
                await message.reply_text(f"❌ Ошибка загрузки: {str(result['message'])[:500]}")
                return
            original_file = str(result['file_path'])
            await self._handle_downloaded_file(message, request, media_paths, original_file)
        except Exception as error:
            logger.exception('Ошибка обработки загрузки')
            await message.reply_text(f"❌ Ошибка: {str(error)[:500]}")

    async def _handle_downloaded_file(self, message, request: DownloadRequest, media_paths: MediaPaths, original_file: str) -> None:
        """Выбирает сценарий отправки после загрузки оригинала."""
        original_size = os.path.getsize(original_file)
        await message.reply_text(build_original_ready_message(format_file_size(original_size)))
        if original_size <= self.settings.telegram_max_size:
            self._run_background_task(
                self._send_original_video(message, request, media_paths, original_file, original_size)
            )
            return
        await self._send_compressed_video(message, request, media_paths, original_file, original_size)

    async def _send_original_video(self, message, request: DownloadRequest, media_paths: MediaPaths, original_file: str, original_size: int) -> None:
        """Отправляет файл без дополнительного сжатия."""
        try:
            with open(original_file, 'rb') as video_file:
                await message.reply_video(
                    video=video_file,
                    caption=build_original_caption(request, format_file_size(original_size)),
                    supports_streaming=True,
                    write_timeout=self.settings.telegram_upload_timeout,
                    read_timeout=self.settings.telegram_upload_timeout,
                    connect_timeout=self.settings.telegram_connect_timeout,
                    pool_timeout=self.settings.telegram_pool_timeout,
                )
            await message.reply_text('✅ Файл отправлен без сжатия.')
        except TimedOut:
            await message.reply_text(
                build_upload_timeout_message(media_paths.relative_path, format_file_size(original_size))
            )
        except Exception as error:
            logger.exception('Ошибка отправки оригинала в Telegram')
            await message.reply_text(f"❌ Ошибка отправки в Telegram: {str(error)[:500]}")

    async def _send_compressed_video(self, message, request: DownloadRequest, media_paths: MediaPaths, original_file: str, original_size: int) -> None:
        """Сжимает файл и отправляет его в Telegram."""
        try:
            compressed = await asyncio.wait_for(
                self._compress_in_executor(original_file, media_paths.compressed_file),
                timeout=self.settings.compression_timeout,
            )
            if not compressed or not os.path.exists(media_paths.compressed_file):
                await message.reply_text(
                    build_compression_failed_message(media_paths.relative_path, format_file_size(original_size))
                )
                return
            self._run_background_task(
                self._reply_with_compressed_video(message, request, media_paths, original_size)
            )
        except asyncio.TimeoutError:
            await message.reply_text(
                build_timeout_message(media_paths.relative_path, format_file_size(original_size))
            )

    async def _reply_with_compressed_video(self, message, request: DownloadRequest, media_paths: MediaPaths, original_size: int) -> None:
        """Отправляет сжатый файл и удаляет временную копию."""
        compressed_size = os.path.getsize(media_paths.compressed_file)
        try:
            with open(media_paths.compressed_file, 'rb') as video_file:
                await message.reply_video(
                    video=video_file,
                    caption=build_compressed_caption(request, original_size, compressed_size),
                    supports_streaming=True,
                    write_timeout=self.settings.telegram_upload_timeout,
                    read_timeout=self.settings.telegram_upload_timeout,
                    connect_timeout=self.settings.telegram_connect_timeout,
                    pool_timeout=self.settings.telegram_pool_timeout,
                )
            await message.reply_text('🧹 Временный файл удалён.')
        except TimedOut:
            await message.reply_text(
                build_upload_timeout_message(media_paths.relative_path, format_file_size(compressed_size))
            )
        except Exception as error:
            logger.exception('Ошибка отправки сжатого файла в Telegram')
            await message.reply_text(f"❌ Ошибка отправки в Telegram: {str(error)[:500]}")
        finally:
            self._remove_file(media_paths.compressed_file)

    async def _compress_in_executor(self, original_file: str, compressed_file: str) -> bool:
        """Запускает сжатие в отдельном потоке."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.compressor.compress, original_file, compressed_file)

    def _run_background_task(self, coroutine) -> None:
        """Запускает неблокирующую фоновую задачу и следит за её ошибками."""
        task = asyncio.create_task(coroutine)
        self._background_tasks.add(task)
        task.add_done_callback(self._finish_background_task)

    def _finish_background_task(self, task: asyncio.Task) -> None:
        """Снимает завершённую задачу с учёта и пишет неожиданные ошибки в лог."""
        self._background_tasks.discard(task)
        try:
            task.result()
        except Exception:
            logger.exception('Фоновая задача завершилась с ошибкой')

    async def _is_authorized(self, update: Update) -> bool:
        """Проверяет доступ пользователя."""
        user_id = update.effective_user.id
        if user_id in self.settings.allowed_user_ids:
            return True
        if update.message:
            await update.message.reply_text('❌ Доступ запрещён')
        elif update.callback_query and update.callback_query.message:
            await update.callback_query.message.reply_text('❌ Доступ запрещён')
        logger.warning('Неавторизованный доступ от пользователя %s', user_id)
        return False

    def run(self) -> None:
        """Запускает polling бота."""
        if not self.settings.bot_token:
            raise RuntimeError('BOT_TOKEN не установлен в переменных окружения')
        self.application = Application.builder().token(self.settings.bot_token).build()
        self.application.add_handler(CommandHandler('start', self.start))
        self.application.add_handler(CommandHandler('status', self.status))
        self.application.add_handler(CallbackQueryHandler(self.handle_genre_choice, pattern=r'^genre:'))
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

    def _genre_keyboard(self) -> InlineKeyboardMarkup:
        """Строит inline-клавиатуру для выбора жанра."""
        rows = []
        current_row = []
        for index, genre in enumerate(self.genre_catalog.genre_options):
            current_row.append(InlineKeyboardButton(genre, callback_data=f'genre:{index}'))
            if len(current_row) == 2:
                rows.append(current_row)
                current_row = []
        if current_row:
            rows.append(current_row)
        rows.append([InlineKeyboardButton('Отмена', callback_data='genre:cancel')])
        return InlineKeyboardMarkup(rows)

    def _genre_from_callback(self, data: str) -> str | None:
        """Возвращает жанр по callback-data."""
        if not data.startswith('genre:'):
            return None
        suffix = data.split(':', 1)[1]
        if suffix == 'cancel':
            return None
        try:
            return self.genre_catalog.genre_options[int(suffix)]
        except (ValueError, IndexError):
            return None

    def _with_canonical_artist(self, request: DownloadRequest) -> DownloadRequest:
        """Возвращает запрос с каноническим именем артиста для каталога и пути хранения."""
        canonical_artist = self.genre_catalog.prepare_artist(request.artist)
        return replace(request, artist=canonical_artist)
