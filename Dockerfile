FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir --upgrade --force-reinstall yt-dlp
RUN python -c "import yt_dlp; print('yt-dlp version:', yt_dlp.version.__version__)"
RUN node --version

COPY . .

CMD ["python", "bot.py"]
