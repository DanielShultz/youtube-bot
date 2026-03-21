FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y curl ffmpeg unzip && \
    rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deno.land/install.sh | sh && \
    ln -s /root/.deno/bin/deno /usr/local/bin/deno

RUN curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp && \
    chmod a+rx /usr/local/bin/yt-dlp

RUN mkdir -p /root/.config/yt-dlp && \
    echo '--js-runtimes deno\n--remote-components ejs:github' > /root/.config/yt-dlp/config

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY kachalnaya_pepega ./kachalnaya_pepega
COPY cookies.txt .

CMD ["python", "-m", "kachalnaya_pepega.main"]