# Качальная Пепега

<p align="center">
  <img src="./logo-round.png" alt="Качальная Пепега" width="220">
</p>

Telegram-бот для скачивания YouTube-видео, сохранения оригиналов на сервере и отправки версии для Telegram.

## Что делает бот

- принимает YouTube-ссылку в Telegram;
- сохраняет оригинал в архив `music-videos`;
- при необходимости сжимает видео под лимиты Telegram;
- отправляет готовую версию обратно в чат;
- раскладывает видео по жанровым папкам и запоминает выбор для новых артистов.

## Важное требование

Для стабильной работы боту нужен приватный `cookies.txt`.

Без него `yt-dlp` чаще определяется YouTube как автоматический клиент, и часть видео перестаёт нормально скачиваться. Поэтому `cookies.txt` практически обязателен, но сам файл не должен попадать в git.

## Структура проекта

- `kachalnaya_pepega/` — код сервиса
- `tests/` — unit-тесты
- `docker-compose.yml` — инфраструктура запуска
- `Dockerfile` — образ приложения
- `.env.example` — пример переменных окружения
- `logo.jpg` — исходный логотип бота
- `logo-round.png` — круглая версия логотипа для README и карточек

## Что нужно для запуска

1. Скопировать `.env.example` в `.env`
2. Заполнить `BOT_TOKEN` и `ALLOWED_USER_IDS`
3. Проверить пути `MEDIA_DIR`, `YTDLP_CONFIG_DIR`, `BOT_DATA_DIR` и `COOKIES_FILE`
4. Положить рабочий `cookies.txt` в корень проекта
5. Запустить `docker compose up -d --build`

## Запуск

- локально: `python -m kachalnaya_pepega.main`
- через Docker: `docker compose up -d --build`

## Переменные окружения

Обязательные настройки в `.env`:

- `BOT_TOKEN`
- `ALLOWED_USER_IDS`
- `TZ`
- `MEDIA_DIR`
- `YTDLP_CONFIG_DIR`
- `BOT_DATA_DIR`
- `COOKIES_FILE`
- `TELEGRAM_UPLOAD_TIMEOUT`
- `TELEGRAM_CONNECT_TIMEOUT`
- `TELEGRAM_POOL_TIMEOUT`

## Тесты

- запуск: `python -m unittest discover -s tests -v`
- покрытие: `python -m coverage run --source=kachalnaya_pepega -m unittest discover -s tests -v`
