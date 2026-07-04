# ruff: noqa: E402

import unittest
from unittest.mock import patch

from fake_telegram import install_telegram_fakes

install_telegram_fakes()

from kachalnaya_pepega.main import configure_logging, main


class MainTests(unittest.TestCase):
    def test_configure_logging_calls_basic_config(self) -> None:
        with patch('kachalnaya_pepega.main.logging.basicConfig') as basic_config:
            configure_logging()
        basic_config.assert_called_once()

    def test_main_configures_logging_and_runs_bot(self) -> None:
        fake_bot = type('FakeBot', (), {'run': lambda self: None})()
        with (
            patch('kachalnaya_pepega.main.configure_logging') as configure,
            patch('kachalnaya_pepega.main.load_settings', return_value='settings') as load_settings,
            patch('kachalnaya_pepega.main.KachalnayaPepegaBot', return_value=fake_bot) as bot_class,
        ):
            main()
        configure.assert_called_once()
        load_settings.assert_called_once()
        bot_class.assert_called_once_with('settings')
