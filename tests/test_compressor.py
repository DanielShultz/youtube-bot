import shutil
import tempfile
import unittest
from pathlib import Path

from kachalnaya_pepega.compressor import VideoCompressor
from unittest.mock import Mock, patch


class CompressorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path('D:/Сервер/docker-projects/youtube-bot/.tmp-tests/compressor')
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)
        self.temp_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)

    def _make_file(self, name: str, size: int) -> str:
        path = self.temp_root / name
        path.write_bytes(b'a' * size)
        return str(path)

    def test_compress_returns_false_for_missing_input(self) -> None:
        compressor = VideoCompressor(100)
        self.assertFalse(compressor.compress('/missing.mp4', '/out.mp4'))

    def test_compress_copies_small_file(self) -> None:
        compressor = VideoCompressor(1000)
        input_path = self._make_file('small.mp4', 3)
        output_path = str(self.temp_root / 'out.mp4')
        with patch.object(compressor, '_copy_file', return_value=True) as copy_file:
            result = compressor.compress(input_path, output_path)
        self.assertTrue(result)
        copy_file.assert_called_once_with(input_path, output_path)

    def test_compress_returns_false_when_primary_compression_fails(self) -> None:
        compressor = VideoCompressor(100)
        input_path = self._make_file('big.mp4', 1000)
        output_path = str(self.temp_root / 'out.mp4')
        with patch.object(compressor, '_get_video_info', return_value={'file_size': 1000, 'height': 1080}):
            with patch.object(compressor, '_compress_video', return_value=False):
                result = compressor.compress(input_path, output_path)
        self.assertFalse(result)

    def test_compress_uses_aggressive_pass_for_large_result(self) -> None:
        compressor = VideoCompressor(100)
        input_path = self._make_file('big2.mp4', 1000)
        output_path = str(self.temp_root / 'out2.mp4')

        def fake_compress(_input: str, out: str, _settings: dict, _timeout: int) -> bool:
            Path(out).write_bytes(b'a' * 200)
            return True

        with patch.object(compressor, '_get_video_info', return_value={'file_size': 1000, 'height': 1080}):
            with patch.object(compressor, '_compress_video', side_effect=fake_compress) as compress_video:
                result = compressor.compress(input_path, output_path)
        self.assertTrue(result)
        self.assertEqual(compress_video.call_count, 2)

    def test_get_video_info_reads_values(self) -> None:
        compressor = VideoCompressor(100)
        input_path = self._make_file('info.mp4', 50)
        with patch.object(compressor, '_read_probe_value', side_effect=[720, 123.4]):
            info = compressor._get_video_info(input_path)
        self.assertEqual(info['height'], 720)
        self.assertEqual(info['duration'], 123.4)
        self.assertEqual(info['file_size'], 50)

    def test_read_probe_value_uses_fallback_on_error(self) -> None:
        compressor = VideoCompressor(100)
        process = Mock(returncode=1, stdout='')
        with patch('kachalnaya_pepega.compressor.subprocess.run', return_value=process):
            value = compressor._read_probe_value('/tmp/in.mp4', 'format=duration', 180.0)
        self.assertEqual(value, 180.0)

    def test_read_probe_value_parses_successful_output(self) -> None:
        compressor = VideoCompressor(100)
        process = Mock(returncode=0, stdout='240\n')
        with patch('kachalnaya_pepega.compressor.subprocess.run', return_value=process):
            value = compressor._read_probe_value('/tmp/in.mp4', 'stream=height', 1080)
        self.assertEqual(value, 240)

    def test_calculate_settings_covers_all_profiles(self) -> None:
        compressor = VideoCompressor(100)
        fast = compressor._calculate_settings({'file_size': 120, 'height': 1080})
        faster = compressor._calculate_settings({'file_size': 220, 'height': 1080})
        veryfast = compressor._calculate_settings({'file_size': 450, 'height': 1080})
        ultrafast = compressor._calculate_settings({'file_size': 1000, 'height': 1080})
        self.assertEqual(fast['preset'], 'fast')
        self.assertEqual(faster['preset'], 'faster')
        self.assertEqual(veryfast['preset'], 'veryfast')
        self.assertEqual(ultrafast['preset'], 'ultrafast')

    def test_aggressive_settings_are_constant(self) -> None:
        compressor = VideoCompressor(100)
        self.assertEqual(compressor._aggressive_settings()['audio_bitrate'], '48k')

    def test_compress_video_returns_true_on_success(self) -> None:
        compressor = VideoCompressor(100)
        process = Mock(returncode=0)
        settings = {'crf': 24, 'preset': 'fast', 'scale_height': 720, 'audio_bitrate': '64k'}
        with patch('kachalnaya_pepega.compressor.subprocess.run', return_value=process):
            result = compressor._compress_video('/tmp/in.mp4', '/tmp/out.mp4', settings, 300)
        self.assertTrue(result)

    def test_compress_video_returns_false_on_exception(self) -> None:
        compressor = VideoCompressor(100)
        settings = {'crf': 24, 'preset': 'fast', 'scale_height': 720, 'audio_bitrate': '64k'}
        with patch('kachalnaya_pepega.compressor.subprocess.run', side_effect=OSError()):
            result = compressor._compress_video('/tmp/in.mp4', '/tmp/out.mp4', settings, 300)
        self.assertFalse(result)

    def test_copy_file_handles_success_and_failure(self) -> None:
        input_path = self._make_file('copy.mp4', 10)
        output_path = str(self.temp_root / 'copy-out.mp4')
        self.assertTrue(VideoCompressor._copy_file(input_path, output_path))
        self.assertTrue(Path(output_path).exists())
        with patch('kachalnaya_pepega.compressor.shutil.copy2', side_effect=OSError()):
            self.assertFalse(VideoCompressor._copy_file('/a', '/b'))