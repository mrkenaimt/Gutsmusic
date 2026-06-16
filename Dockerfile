# build-trigger-2026-06-16-1445
FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y ffmpeg nodejs npm && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir --upgrade --force-reinstall yt-dlp
RUN python -c "import yt_dlp; print('yt-dlp version:', yt_dlp.version.__version__)"
RUN node --version

COPY . .

CMD ["python", "bot.py"]
