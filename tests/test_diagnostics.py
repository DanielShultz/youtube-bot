import unittest

from unittest.mock import Mock, patch

from kachalnaya_pepega.config import Settings
from kachalnaya_pepega.diagnostics import _read_command_output, collect_status_lines


class DiagnosticsTests(unittest.TestCase):
    def test_read_command_output_returns_first_line(self) -> None:
        result = Mock(returncode=0, stdout='line1\nline2\n')
        with patch('kachalnaya_pepega.diagnostics.subprocess.run', return_value=result):
            output = _read_command_output(['cmd'], 5)
        self.assertEqual(output, 'line1')

    def test_read_command_output_handles_failure(self) -> None:
        result = Mock(returncode=1, stdout='')
        with patch('kachalnaya_pepega.diagnostics.subprocess.run', return_value=result):
            output = _read_command_output(['cmd'], 5)
        self.assertEqual(output, 'не доступен')

    def test_collect_status_lines_reports_cookies(self) -> None:
        settings = Settings('Бот', 'token', [1], '/tmp/cookies', '/media', '/data', 45 * 1024 * 1024, 300, 'MV')
        with patch('kachalnaya_pepega.diagnostics._read_command_output', side_effect=['1', '2', '3']):
            with patch('kachalnaya_pepega.diagnostics.os.path.exists', return_value=True):
                lines = collect_status_lines(settings)
        self.assertIn('🔐 cookies: найдены', lines)
        self.assertIn('/start - инструкция', lines)
