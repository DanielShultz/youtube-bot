import sys
import types
from types import SimpleNamespace


def install_telegram_fakes() -> None:
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
