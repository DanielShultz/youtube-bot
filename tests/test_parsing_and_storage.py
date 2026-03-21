import shutil
import unittest
from pathlib import Path

from kachalnaya_pepega.parsing import parse_user_input
from kachalnaya_pepega.storage import build_media_paths, sanitize_component


class ParsingAndStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path('D:/Сервер/docker-projects/youtube-bot/.tmp-tests/storage')
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)
        self.temp_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)

    def test_parse_user_input_reads_quoted_values(self) -> None:
        text = 'https://youtube.com/watch?v=1 "Artist Name" "Song Title" "Music Video"'
        request = parse_user_input(text, 'Default')
        self.assertEqual(request.artist, 'Artist Name')
        self.assertEqual(request.title, 'Song Title')
        self.assertEqual(request.video_type, 'Music Video')

    def test_parse_user_input_uses_defaults(self) -> None:
        request = parse_user_input('https://youtu.be/test', 'Default Type')
        self.assertEqual(request.artist, 'Various')
        self.assertEqual(request.title, 'Unknown')
        self.assertEqual(request.video_type, 'Default Type')

    def test_parse_user_input_rejects_invalid_data(self) -> None:
        self.assertIsNone(parse_user_input('', 'Default'))
        self.assertIsNone(parse_user_input('https://example.com/video', 'Default'))

    def test_sanitize_component_replaces_invalid_characters(self) -> None:
        self.assertEqual(sanitize_component('A:B/C*D'), 'A_B_C_D')

    def test_build_media_paths_creates_structure(self) -> None:
        paths = build_media_paths(str(self.temp_root), 'A/B', 'C:D', 'Live?')
        self.assertEqual(paths.safe_artist, 'A_B')
        self.assertEqual(paths.safe_title, 'C_D')
        self.assertEqual(paths.safe_type, 'Live_')
        self.assertTrue(Path(paths.full_path).exists())
        self.assertIn('A_B - C_D - Live_', paths.filename)