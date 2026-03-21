import sys
import types
import unittest

telegram_module = types.ModuleType('telegram')
telegram_module.Update = type('FakeUpdate', (), {'ALL_TYPES': object()})
telegram_ext_module = types.ModuleType('telegram.ext')
telegram_ext_module.Application = object
telegram_ext_module.CommandHandler = object
telegram_ext_module.ContextTypes = types.SimpleNamespace(DEFAULT_TYPE=object)
telegram_ext_module.MessageHandler = object
telegram_ext_module.filters = types.SimpleNamespace(TEXT=1, COMMAND=2)
sys.modules.setdefault('telegram', telegram_module)
sys.modules.setdefault('telegram.ext', telegram_ext_module)

from unittest.mock import patch

from kachalnaya_pepega.main import configure_logging, main


class MainTests(unittest.TestCase):
    def test_configure_logging_calls_basic_config(self) -> None:
        with patch('kachalnaya_pepega.main.logging.basicConfig') as basic_config:
            configure_logging()
        basic_config.assert_called_once()

    def test_main_configures_logging_and_runs_bot(self) -> None:
        fake_bot = type('FakeBot', (), {'run': lambda self: None})()
        with patch('kachalnaya_pepega.main.configure_logging') as configure:
            with patch('kachalnaya_pepega.main.load_settings', return_value='settings') as load_settings:
                with patch('kachalnaya_pepega.main.KachalnayaPepegaBot', return_value=fake_bot) as bot_class:
                    main()
        configure.assert_called_once()
        load_settings.assert_called_once()
        bot_class.assert_called_once_with('settings')