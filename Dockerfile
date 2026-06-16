FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# كسر الكاش فعلياً: هذا الرقم لازم يتغيّر كل مرة بدك تحدثي yt-dlp
RUN echo "cache-bust-20260616-1" > /tmp/cachebust.txt
RUN pip install --no-cache-dir --upgrade --force-reinstall yt-dlp
RUN python -c "import yt_dlp; print('yt-dlp version:', yt_dlp.version.__version__)"

COPY . .

CMD ["python", "bot.py"]
