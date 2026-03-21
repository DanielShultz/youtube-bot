"""Точка входа сервиса."""

import logging

from .app import KachalnayaPepegaBot
from .config import load_settings


def configure_logging() -> None:
    """Настраивает логирование приложения."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def main() -> None:
    """Запускает сервис."""
    configure_logging()
    KachalnayaPepegaBot(load_settings()).run()


if __name__ == "__main__":
    main()