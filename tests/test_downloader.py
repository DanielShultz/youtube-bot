import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from kachalnaya_pepega.downloader import YouTubeDownloader


class DownloaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path('.tmp-tests/downloader')
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)
        self.temp_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)

    def test_build_command_adds_cookies_when_file_exists(self) -> None:
        downloader = YouTubeDownloader('/tmp/cookies.txt')
        with patch('kachalnaya_pepega.downloader.os.path.exists', return_value=True):
            command = downloader._build_command('https://youtu.be/test', '/tmp/out')
        self.assertIn('--cookies', command)
        self.assertIn('--write-thumbnail', command)
        self.assertIn('--convert-thumbnails', command)

    def test_download_rejects_non_youtube_url(self) -> None:
        downloader = YouTubeDownloader('/tmp/cookies.txt')
        result = downloader.download('https://example.com', '/tmp/out')
        self.assertFalse(result['success'])

    def test_download_handles_subprocess_errors(self) -> None:
        downloader = YouTubeDownloader('/tmp/cookies.txt')
        with patch('kachalnaya_pepega.downloader.subprocess.run', side_effect=subprocess.TimeoutExpired('x', 1)):
            result = downloader.download('https://youtu.be/test', '/tmp/out')
        self.assertIn('Таймаут', result['message'])

    def test_download_returns_file_when_found(self) -> None:
        downloader = YouTubeDownloader('/tmp/cookies.txt')
        process = Mock(returncode=0, stderr='', stdout='')
        with (
            patch('kachalnaya_pepega.downloader.subprocess.run', return_value=process),
            patch.object(downloader, '_find_downloaded_file', return_value='/tmp/video.mp4'),
        ):
            result = downloader.download('https://youtu.be/test', '/tmp/out')
        self.assertTrue(result['success'])
        self.assertEqual(result['file_path'], '/tmp/video.mp4')

    def test_find_downloaded_file_searches_directory(self) -> None:
        downloader = YouTubeDownloader('/tmp/cookies.txt')
        video_path = self.temp_root / 'video.mp4'
        video_path.write_text('x', encoding='utf-8')
        found = downloader._find_downloaded_file(str(self.temp_root / 'missing'))
        self.assertTrue(found.endswith('video.mp4'))

    def test_cleanup_sidecars_removes_download_junk(self) -> None:
        base_path = str(self.temp_root / 'video')
        sidecar = self.temp_root / 'video.part'
        preview = self.temp_root / 'video.jpg'
        keep = self.temp_root / 'video.mp4'
        sidecar.write_text('x', encoding='utf-8')
        preview.write_text('x', encoding='utf-8')
        keep.write_text('x', encoding='utf-8')
        YouTubeDownloader._cleanup_sidecars(base_path)
        self.assertFalse(sidecar.exists())
        self.assertTrue(preview.exists())
        self.assertTrue(keep.exists())

    def test_extract_error_formats_unavailable_video(self) -> None:
        process = Mock(
            stderr='ERROR: [youtube] b8m9zhNAgKs: Video unavailable. This video is not available',
            stdout='',
        )
        message = YouTubeDownloader._extract_error(process)
        self.assertEqual(message, 'Видео недоступно на YouTube: удалено, скрыто или ограничено.')
