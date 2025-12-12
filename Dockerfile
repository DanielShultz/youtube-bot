FROM python:3.11-slim

WORKDIR /app

# Установка всех зависимостей включая Deno (рекомендуемый JavaScript runtime)
RUN apt-get update && \
    apt-get install -y curl ffmpeg unzip && \
    rm -rf /var/lib/apt/lists/*

# Устанавливаем Deno (рекомендуемый JavaScript runtime для yt-dlp)
RUN curl -fsSL https://deno.land/install.sh | sh && \
    ln -s /root/.deno/bin/deno /usr/local/bin/deno

# Устанавливаем yt-dlp
RUN curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp && \
    chmod a+rx /usr/local/bin/yt-dlp

# Создаем конфигурационный файл для yt-dlp с настройками EJS
RUN mkdir -p /root/.config/yt-dlp && \
    echo '--js-runtimes deno\n--remote-components ejs:github' > /root/.config/yt-dlp/config

# Копируем requirements и устанавливаем Python пакеты
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бота
COPY bot.py .
COPY cookies.txt .

CMD ["python", "bot.py"]