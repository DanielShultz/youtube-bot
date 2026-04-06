import os
import sys
import tempfile
import types
import unittest

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

telegram_module = types.ModuleType('telegram')
telegram_module.Update = type('FakeUpdate', (), {'ALL_TYPES': object()})
telegram_module.InlineKeyboardButton = lambda text, callback_data=None: ('button', text, callback_data)
telegram_module.InlineKeyboardMarkup = lambda rows: ('markup', rows)
telegram_error_module = types.ModuleType('telegram.error')
telegram_error_module.TimedOut = type('TimedOut', (Exception,), {})
telegram_ext_module = types.ModuleType('telegram.ext')
telegram_ext_module.ContextTypes = SimpleNamespace(DEFAULT_TYPE=object)
telegram_ext_module.filters = SimpleNamespace(TEXT=1, COMMAND=2)
telegram_ext_module.CommandHandler = lambda *args, **kwargs: ('command', args)
telegram_ext_module.MessageHandler = lambda *args, **kwargs: ('message', args)
telegram_ext_module.CallbackQueryHandler = lambda *args, **kwargs: ('callback', args, kwargs)
telegram_ext_module.Application = object
sys.modules.setdefault('telegram', telegram_module)
sys.modules.setdefault('telegram.error', telegram_error_module)
sys.modules.setdefault('telegram.ext', telegram_ext_module)

from telegram.error import TimedOut

from kachalnaya_pepega.app import KachalnayaPepegaBot, PENDING_REQUEST_KEY
from kachalnaya_pepega.config import Settings
from kachalnaya_pepega.parsing import DownloadRequest
from kachalnaya_pepega.storage import MediaPaths


class FakeMessage:
    def __init__(self, text: str = 'https://youtu.be/test') -> None:
        self.text = text
        self.reply_text = AsyncMock()
        self.reply_video = AsyncMock()


class FakeCallbackQuery:
    def __init__(self, data: str, message: FakeMessage | None = None) -> None:
        self.data = data
        self.message = message or FakeMessage()
        self.answer = AsyncMock()
        self.edit_message_text = AsyncMock()


class FakeApplication:
    def __init__(self) -> None:
        self.handlers = []
        self.run_polling = Mock()

    def add_handler(self, handler) -> None:
        self.handlers.append(handler)


class FakeBuilder:
    def __init__(self, app: FakeApplication) -> None:
        self.app = app

    def token(self, value: str):
        return self

    def build(self) -> FakeApplication:
        return self.app


class FakeGenreCatalog:
    def __init__(self, genre: str | None = 'MV') -> None:
        self.genre = genre
        self.saved = []
        self.genre_options = [
            'K-Pop - Idol',
            'K-Hip-Hop - Asian Alt',
            'Hip-Hop - Trap',
            'Pop - Dance',
            'Rock - Metal',
            'Industrial - Electronic - Experimental',
        ]

    def resolve(self, artist: str) -> str | None:
        return self.genre

    def assign(self, artist: str, genre: str) -> str:
        canonical = self.prepare_artist(artist)
        self.saved.append((canonical, genre))
        self.genre = genre
        return canonical

    def prepare_artist(self, artist: str) -> str:
        if artist.casefold() == 'ateez':
            return 'ATEEZ'
        return ' '.join(artist.split())


class AppTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        settings = Settings('???', 'token', [1], '/cookies', '/media', '/data', 10, 1, 600, 60, 60, 'MV')
        self.bot = KachalnayaPepegaBot(settings)
        self.bot.genre_catalog = FakeGenreCatalog('MV')

    async def test_start_and_status_send_messages(self) -> None:
        update = SimpleNamespace(effective_user=SimpleNamespace(id=1), message=FakeMessage(), callback_query=None)
        await self.bot.start(update, None)
        with patch('kachalnaya_pepega.app.collect_status_lines', return_value=['a', 'b']):
            await self.bot.status(update, None)
        self.assertEqual(update.message.reply_text.await_count, 2)

    async def test_handle_download_rejects_invalid_input(self) -> None:
        update = SimpleNamespace(effective_user=SimpleNamespace(id=1), message=FakeMessage('bad'), callback_query=None)
        await self.bot.handle_download(update, SimpleNamespace(user_data={}))
        update.message.reply_text.assert_awaited_once()

    async def test_handle_download_processes_valid_request(self) -> None:
        update = SimpleNamespace(effective_user=SimpleNamespace(id=1), message=FakeMessage(), callback_query=None)
        request = DownloadRequest('u', 'ateez', 'b', 'c')
        with patch('kachalnaya_pepega.app.parse_user_input', return_value=request):
            with patch.object(self.bot, '_start_download', new=AsyncMock()) as start_download:
                await self.bot.handle_download(update, SimpleNamespace(user_data={}))
        start_download.assert_awaited_once_with(update.message, DownloadRequest('u', 'ATEEZ', 'b', 'c'), 'MV')

    async def test_handle_download_asks_for_genre_when_unknown_artist(self) -> None:
        self.bot.genre_catalog = FakeGenreCatalog(None)
        update = SimpleNamespace(effective_user=SimpleNamespace(id=1), message=FakeMessage(), callback_query=None)
        request = DownloadRequest('u', 'New Artist', 'b', 'c')
        context = SimpleNamespace(user_data={})
        with patch('kachalnaya_pepega.app.parse_user_input', return_value=request):
            await self.bot.handle_download(update, context)
        self.assertIn(PENDING_REQUEST_KEY, context.user_data)
        self.assertEqual(context.user_data[PENDING_REQUEST_KEY]['artist'], 'New Artist')
        update.message.reply_text.assert_awaited_once()

    async def test_handle_genre_choice_saves_and_starts_download(self) -> None:
        self.bot.genre_catalog = FakeGenreCatalog(None)
        context = SimpleNamespace(user_data={PENDING_REQUEST_KEY: {
            'url': 'u', 'artist': 'New Artist', 'title': 'Song', 'video_type': 'MV'
        }})
        query = FakeCallbackQuery('genre:1')
        update = SimpleNamespace(effective_user=SimpleNamespace(id=1), message=None, callback_query=query)
        with patch.object(self.bot, '_start_download', new=AsyncMock()) as start_download:
            await self.bot.handle_genre_choice(update, context)
        self.assertEqual(self.bot.genre_catalog.saved, [('New Artist', 'K-Hip-Hop - Asian Alt')])
        start_download.assert_awaited_once_with(query.message, DownloadRequest('u', 'New Artist', 'Song', 'MV'), 'K-Hip-Hop - Asian Alt')
        self.assertNotIn(PENDING_REQUEST_KEY, context.user_data)

    def test_with_canonical_artist_uses_catalog_name(self) -> None:
        request = DownloadRequest('u', 'ateez', 'Song', 'MV')
        canonical = self.bot._with_canonical_artist(request)
        self.assertEqual(canonical.artist, 'ATEEZ')

    async def test_is_authorized_accepts_known_user(self) -> None:
        update = SimpleNamespace(effective_user=SimpleNamespace(id=1), message=FakeMessage(), callback_query=None)
        self.assertTrue(await self.bot._is_authorized(update))

    async def test_is_authorized_rejects_unknown_user(self) -> None:
        update = SimpleNamespace(effective_user=SimpleNamespace(id=2), message=FakeMessage(), callback_query=None)
        self.assertFalse(await self.bot._is_authorized(update))
        update.message.reply_text.assert_awaited_once()

    async def test_process_download_reports_failure_and_exception(self) -> None:
        message = FakeMessage()
        request = DownloadRequest('u', 'a', 'b', 'c')
        paths = MediaPaths('/tmp', 'a/b', 'g', 'a', 'b', 'c', 'f', '/tmp/f.mp4', '/tmp/f_t.mp4')
        with patch.object(self.bot.downloader, 'download', return_value={'success': False, 'message': 'err'}):
            await self.bot._process_download(message, request, paths)
        with patch.object(self.bot.downloader, 'download', side_effect=RuntimeError('boom')):
            await self.bot._process_download(message, request, paths)
        self.assertEqual(message.reply_text.await_count, 2)

    async def test_handle_downloaded_file_chooses_branch_by_size(self) -> None:
        message = FakeMessage()
        request = DownloadRequest('u', 'a', 'b', 'c')
        paths = MediaPaths('/tmp', 'a/b', 'g', 'a', 'b', 'c', 'f', '/tmp/f.mp4', '/tmp/f_t.mp4')
        with tempfile.NamedTemporaryFile(delete=False) as file:
            file.write(b'abc')
            file_path = file.name
        with patch.object(self.bot, '_send_original_video', new=Mock(return_value=object())) as send_original:
            with patch.object(self.bot, '_run_background_task') as run_background_task:
                await self.bot._handle_downloaded_file(message, request, paths, file_path)
        self.bot.settings = Settings('???', 'token', [1], '/cookies', '/media', '/data', 1, 1, 600, 60, 60, 'MV')
        with patch.object(self.bot, '_send_compressed_video', new=AsyncMock()) as send_compressed:
            await self.bot._handle_downloaded_file(message, request, paths, file_path)
        send_original.assert_called_once()
        run_background_task.assert_called_once()
        send_compressed.assert_awaited_once()
        os.remove(file_path)

    async def test_send_original_video_uses_extended_timeouts(self) -> None:
        message = FakeMessage()
        request = DownloadRequest('u', 'a', 'b', 'c')
        paths = MediaPaths('/tmp', 'a/b', 'g', 'a', 'b', 'c', 'f', '/tmp/f.mp4', '/tmp/f_t.mp4')
        with tempfile.NamedTemporaryFile(delete=False) as file:
            file.write(b'abc')
            file_path = file.name
        await self.bot._send_original_video(message, request, paths, file_path, 3)
        _, kwargs = message.reply_video.await_args
        self.assertEqual(kwargs['write_timeout'], 600)
        self.assertEqual(kwargs['read_timeout'], 600)
        self.assertEqual(kwargs['connect_timeout'], 60)
        self.assertEqual(kwargs['pool_timeout'], 60)
        os.remove(file_path)

    async def test_send_original_video_reports_upload_timeout(self) -> None:
        message = FakeMessage()
        request = DownloadRequest('u', 'a', 'b', 'c')
        paths = MediaPaths('/tmp', 'a/b', 'g', 'a', 'b', 'c', 'f', '/tmp/f.mp4', '/tmp/f_t.mp4')
        with tempfile.NamedTemporaryFile(delete=False) as file:
            file.write(b'abc')
            file_path = file.name
        message.reply_video.side_effect = TimedOut('Timed out')
        await self.bot._send_original_video(message, request, paths, file_path, 3)
        message.reply_text.assert_awaited_once()
        self.assertIn('a/b', message.reply_text.await_args.args[0])
        os.remove(file_path)

    async def test_send_compressed_video_handles_timeout_and_failure(self) -> None:
        message = FakeMessage()
        request = DownloadRequest('u', 'a', 'b', 'c')
        paths = MediaPaths('/tmp', 'a/b', 'g', 'a', 'b', 'c', 'f', '/tmp/f.mp4', '/tmp/f_t.mp4')
        with patch.object(self.bot, '_compress_in_executor', new=Mock(return_value=object())):
            with patch('kachalnaya_pepega.app.asyncio.wait_for', side_effect=TimeoutError()):
                await self.bot._send_compressed_video(message, request, paths, '/tmp/in.mp4', 100)
        with patch.object(self.bot, '_compress_in_executor', new=Mock(return_value=object())):
            with patch('kachalnaya_pepega.app.asyncio.wait_for', new=AsyncMock(return_value=False)):
                with patch('kachalnaya_pepega.app.os.path.exists', return_value=False):
                    await self.bot._send_compressed_video(message, request, paths, '/tmp/in.mp4', 100)
        self.assertEqual(message.reply_text.await_count, 2)

    async def test_reply_with_compressed_video_sends_file(self) -> None:
        message = FakeMessage()
        request = DownloadRequest('u', 'a', 'b', 'c')
        with tempfile.NamedTemporaryFile(delete=False) as file:
            file.write(b'abc')
            temp_path = file.name
        paths = MediaPaths('/tmp', 'a/b', 'g', 'a', 'b', 'c', 'f', '/tmp/f.mp4', temp_path)
        await self.bot._reply_with_compressed_video(message, request, paths, 100)
        message.reply_video.assert_awaited_once()
        _, kwargs = message.reply_video.await_args
        self.assertEqual(kwargs['write_timeout'], 600)
        self.assertEqual(kwargs['read_timeout'], 600)
        self.assertEqual(kwargs['connect_timeout'], 60)
        self.assertEqual(kwargs['pool_timeout'], 60)
        message.reply_text.assert_awaited_once()
        self.assertFalse(os.path.exists(temp_path))

    async def test_reply_with_compressed_video_reports_upload_timeout(self) -> None:
        message = FakeMessage()
        request = DownloadRequest('u', 'a', 'b', 'c')
        with tempfile.NamedTemporaryFile(delete=False) as file:
            file.write(b'abc')
            temp_path = file.name
        paths = MediaPaths('/tmp', 'a/b', 'g', 'a', 'b', 'c', 'f', '/tmp/f.mp4', temp_path)
        message.reply_video.side_effect = TimedOut('Timed out')
        await self.bot._reply_with_compressed_video(message, request, paths, 100)
        message.reply_text.assert_awaited_once()
        self.assertIn('a/b', message.reply_text.await_args.args[0])
        self.assertFalse(os.path.exists(temp_path))

    def test_run_without_token_raises_error(self) -> None:
        bot = KachalnayaPepegaBot(Settings('???', '', [1], '/c', '/m', '/d', 10, 1, 600, 60, 60, 'MV'))
        with self.assertRaises(RuntimeError):
            bot.run()

    def test_run_registers_handlers(self) -> None:
        fake_app = FakeApplication()
        fake_builder = FakeBuilder(fake_app)
        fake_application = type('FakeApplicationType', (), {'builder': staticmethod(lambda: fake_builder)})
        bot = KachalnayaPepegaBot(Settings('???', 'token', [1], '/c', '/m', '/d', 10, 1, 600, 60, 60, 'MV'))
        with patch('kachalnaya_pepega.app.Application', fake_application):
            bot.run()
        self.assertEqual(len(fake_app.handlers), 4)
        fake_app.run_polling.assert_called_once()

    def test_remove_file_deletes_existing_path(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as file:
            path = file.name
        self.bot._remove_file(path)
        self.assertFalse(os.path.exists(path))
