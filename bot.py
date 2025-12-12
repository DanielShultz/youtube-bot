import os
import subprocess
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройки из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
ALLOWED_USERS = [int(x) for x in os.getenv('ALLOWED_USER_IDS', '').split(',') if x]

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Доступ запрещен")
        logger.warning(f"Unauthorized access attempt from user {user_id}")
        return
    
    await update.message.reply_text(
        "🎬 YouTube Download Bot\n\n"
        "Отправьте YouTube ссылку для скачивания\n"
        "Формат:\n"
        "URL [артист] [название] [тип]\n\n"
        "Пример:\n"
        "https://youtube.com/watch?v=... \"Artist Name\" \"Song Title\" \"Music Video\"\n\n"
        "Типы видео по умолчанию: Music Video\n"
        "Качество: 1080p"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Доступ запрещен")
        return
        
    # Проверяем доступность cookies
    cookies_path = "/app/cookies.txt"
    cookies_status = "✅ Найден" if os.path.exists(cookies_path) else "❌ Не найден"
    
    # Проверяем доступность yt-dlp
    try:
        yt_dlp_result = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True)
        yt_dlp_status = "✅ Доступен" if yt_dlp_result.returncode == 0 else "❌ Не доступен"
        yt_dlp_version = f" ({yt_dlp_result.stdout.strip()})" if yt_dlp_result.returncode == 0 else ""
    except:
        yt_dlp_status = "❌ Ошибка проверки"
        yt_dlp_version = ""
    
    # Проверяем ffmpeg
    try:
        ffmpeg_result = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True)
        ffmpeg_status = "✅ Установлен" if ffmpeg_result.returncode == 0 else "❌ Не установлен"
    except:
        ffmpeg_status = "❌ Ошибка проверки"
    
    # Проверяем Deno
    try:
        deno_result = subprocess.run(["deno", "--version"], capture_output=True, text=True)
        deno_status = "✅ Установлен" if deno_result.returncode == 0 else "❌ Не установлен"
        if deno_result.returncode == 0:
            deno_version_line = deno_result.stdout.split('\n')[0]
            deno_version = f" ({deno_version_line})"
        else:
            deno_version = ""
    except:
        deno_status = "❌ Ошибка проверки"
        deno_version = ""
    
    status_message = (
        "🤖 Статус бота\n\n"
        "Зависимости:\n"
        f"• yt-dlp {yt_dlp_status}{yt_dlp_version}\n"
        f"• ffmpeg {ffmpeg_status}\n"
        f"• Deno {deno_status}{deno_version}\n"
        f"• Cookies {cookies_status}\n\n"
        "Качество: 1080p\n"
        "Тип видео по умолчанию: Music Video\n\n"
        "Команды:\n"
        "• /start - начать работу\n"
        "• /status - статус системы\n"
        "• Отправьте YouTube ссылку для загрузки"
    )
    
    await update.message.reply_text(status_message)

async def handle_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Доступ запрещен")
        return

    text = update.message.text.strip()
    
    if not text:
        await update.message.reply_text("📝 Отправьте YouTube ссылку")
        return

    # Улучшенный парсинг: ищем URL и затем артиста/название/тип в кавычках
    import shlex
    try:
        parts = shlex.split(text)  # Правильно обрабатывает кавычки
    except:
        parts = text.split()  # Fallback на простой split
    
    if not parts:
        await update.message.reply_text("📝 Отправьте YouTube ссылку")
        return

    url = parts[0]
    
    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("❌ Пожалуйста, отправьте корректную YouTube ссылку")
        return

    # Артист, название и тип - все остальные части
    if len(parts) >= 4:
        artist = parts[1]
        title = parts[2]
        video_type = ' '.join(parts[3:])  # Объединяем все оставшиеся части в тип
    elif len(parts) == 3:
        artist = parts[1]
        title = parts[2]
        video_type = "Music Video"  # Тип по умолчанию
    elif len(parts) == 2:
        artist = parts[1]
        title = "Unknown"
        video_type = "Music Video"  # Тип по умолчанию
    else:
        artist = "Various"
        title = "Unknown"
        video_type = "Music Video"  # Тип по умолчанию

    # Убираем кавычки если они есть
    artist = artist.strip('"\'')
    title = title.strip('"\'')
    video_type = video_type.strip('"\'')

    # Создаем безопасные имена для папок и файлов
    def safe_filename(name):
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name.strip()

    safe_artist = safe_filename(artist)
    safe_title = safe_filename(title)
    safe_type = safe_filename(video_type)

    # Создаем структуру папок: Артист/Название трека/
    base_path = f"/media/music-videos/{safe_artist}/{safe_title}"
    os.makedirs(base_path, exist_ok=True)

    # Формируем имя файла: Артист - Название трека - Тип
    filename = f"{safe_artist} - {safe_title} - {safe_type}"

    await update.message.reply_text(
        f"⏬ Начинаю загрузку...\n"
        f"Артист: {artist}\n"
        f"Название: {title}\n"
        f"Тип: {video_type}\n"
        f"Качество: 1080p\n"
        f"Путь: {safe_artist}/{safe_title}/\n\n"
        f"Это может занять несколько минут..."
    )

    try:
        # Проверяем наличие cookies файла
        cookies_path = "/app/cookies.txt"
        
        # Базовые параметры yt-dlp с EJS настройками
        command = [
            "yt-dlp",
            "-o", f"{base_path}/{filename}.%(ext)s",
            "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
            "--write-thumbnail",
            "--convert-thumbnails", "jpg",
            "--ffmpeg-location", "/usr/bin",
            # Настройки EJS для решения JavaScript challenges
            "--js-runtimes", "deno",
            "--remote-components", "ejs:github",
            # Отключаем сохранение cookies чтобы избежать ошибки Read-only file system
            "--no-cookies",
            # Параметры для надежности
            "--retries", "3",
            "--fragment-retries", "3",
            "--ignore-errors",
        ]
        
        # Добавляем cookies только для чтения если файл существует
        if os.path.exists(cookies_path):
            command.extend(["--cookies", cookies_path])
            await update.message.reply_text("🔐 Использую cookies для аутентификации...")
        else:
            await update.message.reply_text("⚠️ Cookies не найдены, пробую без аутентификации...")
        
        command.append(url)
        
        result = subprocess.run(command, capture_output=True, text=True, timeout=600)

        if result.returncode == 0:
            success_message = (
                f"✅ Загрузка завершена успешно!\n"
                f"Артист: {artist}\n"
                f"Название: {title}\n"
                f"Тип: {video_type}\n"
                f"Файл: {filename}.mp4\n"
                f"Путь: {safe_artist}/{safe_title}/"
            )
            await update.message.reply_text(success_message)
            logger.info(f"Download completed: {artist} - {title} - {video_type}")
                
        else:
            error_msg = result.stderr or "Неизвестная ошибка"
            error_message = f"❌ Ошибка при загрузке\n{error_msg[-500:]}"
            await update.message.reply_text(error_message)
            logger.error(f"Download failed: {error_msg}")

    except subprocess.TimeoutExpired:
        await update.message.reply_text("⏰ Таймаут загрузки")
    except Exception as e:
        error_message = f"❌ Ошибка бота:\n{str(e)}"
        await update.message.reply_text(error_message)
        logger.error(f"Bot error: {str(e)}")
        
def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set in environment variables")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_download))

    # Запуск бота
    logger.info("Bot starting...")
    application.run_polling()

if __name__ == "__main__":
    main()