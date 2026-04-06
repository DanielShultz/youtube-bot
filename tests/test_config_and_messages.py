import unittest

from unittest.mock import patch

from kachalnaya_pepega.config import Settings, _parse_allowed_user_ids, load_settings
from kachalnaya_pepega.messages import (
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
from kachalnaya_pepega.parsing import DownloadRequest


class ConfigAndMessagesTests(unittest.TestCase):
    def test_parse_allowed_user_ids_skips_empty_values(self) -> None:
        self.assertEqual(_parse_allowed_user_ids('1,2,,3'), [1, 2, 3])

    def test_load_settings_reads_environment(self) -> None:
        env = {
            'BOT_TOKEN': 'abc',
            'ALLOWED_USER_IDS': '10,11',
            'TELEGRAM_UPLOAD_TIMEOUT': '700',
            'TELEGRAM_CONNECT_TIMEOUT': '70',
            'TELEGRAM_POOL_TIMEOUT': '80',
        }
        with patch.dict('os.environ', env, clear=True):
            settings = load_settings()
        self.assertEqual(settings.bot_name, 'Качальная Пепега')
        self.assertEqual(settings.bot_token, 'abc')
        self.assertEqual(settings.allowed_user_ids, [10, 11])
        self.assertEqual(settings.bot_data_path, '/app/data')
        self.assertEqual(settings.telegram_upload_timeout, 700)
        self.assertEqual(settings.telegram_connect_timeout, 70)
        self.assertEqual(settings.telegram_pool_timeout, 80)

    def test_start_message_contains_bot_name(self) -> None:
        settings = Settings('Качальная Пепега', 't', [1], '/c', '/m', '/d', 1, 1, 600, 60, 60, 'Music Video')
        self.assertIn('Качальная Пепега', build_start_message(settings))

    def test_download_and_ready_messages_include_fields(self) -> None:
        request = DownloadRequest('u', 'Artist', 'Title', 'Live')
        started = build_download_started_message(request, 'Pop - Dance')
        self.assertIn('Artist', started)
        self.assertIn('Жанр: Pop - Dance', started)
        self.assertIn('12.0 MB', build_original_ready_message('12.0 MB'))

    def test_captions_and_error_messages_include_context(self) -> None:
        request = DownloadRequest('u', 'Artist', 'Title', 'Clip')
        compressed = build_compressed_caption(request, 100, 50)
        self.assertIn('Artist', build_original_caption(request, '10 MB'))
        self.assertIn('50.0%', compressed)
        self.assertIn('a/b', build_timeout_message('a/b', '10 MB'))
        self.assertIn('a/b', build_compression_failed_message('a/b', '10 MB'))
        self.assertIn('a/b', build_upload_timeout_message('a/b', '10 MB'))

    def test_format_file_size_handles_zero_and_units(self) -> None:
        self.assertEqual(format_file_size(0), '0 B')
        self.assertEqual(format_file_size(1024), '1.0 KB')
