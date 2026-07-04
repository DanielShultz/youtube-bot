import unittest

from kachalnaya_pepega.parsing import normalize_youtube_url, parse_user_input


class ParsingTests(unittest.TestCase):
    def test_normalize_watch_url_with_playlist_query(self) -> None:
        self.assertEqual(
            normalize_youtube_url('https://www.youtube.com/watch?v=ST9ib_nbizU&list=RDST9ib_nbizU&start_radio=1'),
            'https://youtu.be/ST9ib_nbizU',
        )

    def test_normalize_short_url_with_playlist_query(self) -> None:
        self.assertEqual(
            normalize_youtube_url('https://youtu.be/Y5uwDZGgX7E?list=RDY5uwDZGgX7E'),
            'https://youtu.be/Y5uwDZGgX7E',
        )

    def test_parse_user_input_uses_normalized_url(self) -> None:
        request = parse_user_input(
            'https://www.youtube.com/watch?v=ST9ib_nbizU&list=RDST9ib_nbizU&start_radio=1 '
            '"ATEEZ" "Ice On My Teeth" "Live 2024 MBC"',
            'MV',
        )
        self.assertIsNotNone(request)
        assert request is not None
        self.assertEqual(request.url, 'https://youtu.be/ST9ib_nbizU')
        self.assertEqual(request.artist, 'ATEEZ')
        self.assertEqual(request.title, 'Ice On My Teeth')
        self.assertEqual(request.video_type, 'Live 2024 MBC')


if __name__ == '__main__':
    unittest.main()
