import os
import sys
import tempfile
import types
import unittest

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

telegram_module = types.ModuleType('telegram')
telegram_module.Update = type('FakeUpdate', (), {'ALL_TYPES': object()})
telegram_ext_module = types.ModuleType('telegram.ext')
telegram_ext_module.ContextTypes = SimpleNamespace(DEFAULT_TYPE=object)
telegram_ext_module.filters = SimpleNamespace(TEXT=1, COMMAND=2)
telegram_ext_module.CommandHandler = lambda *args, **kwargs: ('command', args)
telegram_ext_module.MessageHandler = lambda *args, **kwargs: ('message', args)
telegram_ext_module.Application = object
sys.modules.setdefault('telegram', telegram_module)
sys.modules.setdefault('telegram.ext', telegram_ext_module)

from kachalnaya_pepega.app import KachalnayaPepegaBot
from kachalnaya_pepega.config import Settings
from kachalnaya_pepega.parsing import DownloadRequest
from kachalnaya_pepega.storage import MediaPaths


class FakeMessage:
    def __init__(self, text: str = 'https://youtu.be/test') -> None:
        self.text = text
        self.reply_text = AsyncMock()
        self.reply_video = AsyncMock()


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


class AppTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        settings = Settings('Бот', 'token', [1], '/cookies', '/media', 10, 1, 'MV')
        self.bot = KachalnayaPepegaBot(settings)

    async def test_start_and_status_send_messages(self) -> None:
        update = SimpleNamespace(effective_user=SimpleNamespace(id=1), message=FakeMessage())
        await self.bot.start(update, None)
        with patch('kachalnaya_pepega.app.collect_status_lines', return_value=['a', 'b']):
            await self.bot.status(update, None)
        self.assertEqual(update.message.reply_text.await_count, 2)

    async def test_handle_download_rejects_invalid_input(self) -> None:
        update = SimpleNamespace(effective_user=SimpleNamespace(id=1), message=FakeMessage('bad'))
        await self.bot.handle_download(update, None)
        update.message.reply_text.assert_awaited_once()

    async def test_handle_download_processes_valid_request(self) -> None:
        update = SimpleNamespace(effective_user=SimpleNamespace(id=1), message=FakeMessage())
        request = DownloadRequest('u', 'a', 'b', 'c')
        with patch('kachalnaya_pepega.app.parse_user_input', return_value=request):
            with patch('kachalnaya_pepega.app.build_media_paths') as build_paths:
                with patch.object(self.bot, '_process_download', new=AsyncMock()) as process_download:
                    await self.bot.handle_download(update, None)
        build_paths.assert_called_once()
        process_download.assert_awaited_once()

    async def test_is_authorized_accepts_known_user(self) -> None:
        update = SimpleNamespace(effective_user=SimpleNamespace(id=1), message=FakeMessage())
        self.assertTrue(await self.bot._is_authorized(update))

    async def test_is_authorized_rejects_unknown_user(self) -> None:
        update = SimpleNamespace(effective_user=SimpleNamespace(id=2), message=FakeMessage())
        self.assertFalse(await self.bot._is_authorized(update))
        update.message.reply_text.assert_awaited_once()

    async def test_process_download_reports_failure_and_exception(self) -> None:
        update = SimpleNamespace(effective_user=SimpleNamespace(id=1), message=FakeMessage())
        request = DownloadRequest('u', 'a', 'b', 'c')
        paths = MediaPaths('/tmp', 'a/b', 'a', 'b', 'c', 'f', '/tmp/f.mp4', '/tmp/f_t.mp4')
        with patch.object(self.bot.downloader, 'download', return_value={'success': False, 'message': 'err'}):
            await self.bot._process_download(update, request, paths)
        with patch.object(self.bot.downloader, 'download', side_effect=RuntimeError('boom')):
            await self.bot._process_download(update, request, paths)
        self.assertEqual(update.message.reply_text.await_count, 2)

    async def test_handle_downloaded_file_chooses_branch_by_size(self) -> None:
        update = SimpleNamespace(effective_user=SimpleNamespace(id=1), message=FakeMessage())
        request = DownloadRequest('u', 'a', 'b', 'c')
        paths = MediaPaths('/tmp', 'a/b', 'a', 'b', 'c', 'f', '/tmp/f.mp4', '/tmp/f_t.mp4')
        with tempfile.NamedTemporaryFile(delete=False) as file:
            file.write(b'abc')
            file_path = file.name
        with patch.object(self.bot, '_send_original_video', new=AsyncMock()) as send_original:
            await self.bot._handle_downloaded_file(update, request, paths, file_path)
        self.bot.settings = Settings('Бот', 'token', [1], '/cookies', '/media', 1, 1, 'MV')
        with patch.object(self.bot, '_send_compressed_video', new=AsyncMock()) as send_compressed:
            await self.bot._handle_downloaded_file(update, request, paths, file_path)
        send_original.assert_awaited_once()
        send_compressed.assert_awaited_once()
        os.remove(file_path)

    async def test_send_compressed_video_handles_timeout_and_failure(self) -> None:
        update = SimpleNamespace(effective_user=SimpleNamespace(id=1), message=FakeMessage())
        request = DownloadRequest('u', 'a', 'b', 'c')
        paths = MediaPaths('/tmp', 'a/b', 'a', 'b', 'c', 'f', '/tmp/f.mp4', '/tmp/f_t.mp4')
        with patch.object(self.bot, '_compress_in_executor', new=Mock(return_value=object())):
            with patch('kachalnaya_pepega.app.asyncio.wait_for', side_effect=TimeoutError()):
                await self.bot._send_compressed_video(update, request, paths, '/tmp/in.mp4', 100)
        with patch.object(self.bot, '_compress_in_executor', new=Mock(return_value=object())):
            with patch('kachalnaya_pepega.app.asyncio.wait_for', new=AsyncMock(return_value=False)):
                with patch('kachalnaya_pepega.app.os.path.exists', return_value=False):
                    await self.bot._send_compressed_video(update, request, paths, '/tmp/in.mp4', 100)
        self.assertEqual(update.message.reply_text.await_count, 2)

    async def test_reply_with_compressed_video_sends_file(self) -> None:
        update = SimpleNamespace(effective_user=SimpleNamespace(id=1), message=FakeMessage())
        request = DownloadRequest('u', 'a', 'b', 'c')
        with tempfile.NamedTemporaryFile(delete=False) as file:
            file.write(b'abc')
            temp_path = file.name
        paths = MediaPaths('/tmp', 'a/b', 'a', 'b', 'c', 'f', '/tmp/f.mp4', temp_path)
        await self.bot._reply_with_compressed_video(update, request, paths, 100)
        update.message.reply_video.assert_awaited_once()
        update.message.reply_text.assert_awaited_once()

    def test_run_without_token_raises_error(self) -> None:
        bot = KachalnayaPepegaBot(Settings('Бот', '', [1], '/c', '/m', 10, 1, 'MV'))
        with self.assertRaises(RuntimeError):
            bot.run()

    def test_run_registers_handlers(self) -> None:
        fake_app = FakeApplication()
        fake_builder = FakeBuilder(fake_app)
        fake_application = type('FakeApplicationType', (), {'builder': staticmethod(lambda: fake_builder)})
        bot = KachalnayaPepegaBot(Settings('Бот', 'token', [1], '/c', '/m', 10, 1, 'MV'))
        with patch('kachalnaya_pepega.app.Application', fake_application):
            bot.run()
        self.assertEqual(len(fake_app.handlers), 3)
        fake_app.run_polling.assert_called_once()

    def test_remove_file_deletes_existing_path(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as file:
            path = file.name
        self.bot._remove_file(path)
        self.assertFalse(os.path.exists(path))