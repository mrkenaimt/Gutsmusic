# build-trigger-2026-06-16-deno
FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl unzip ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# تنصيب Deno (JS runtime يحتاجه yt-dlp لحل تحديات يوتيوب)
RUN curl -fsSL https://deno.land/install.sh | sh
ENV DENO_INSTALL="/root/.deno"
ENV PATH="$DENO_INSTALL/bin:$PATH"

# تأكيد إلزامي: لو deno غير موجود، البناء يفشل هنا
RUN deno --version && echo "✅ Deno مثبت بنجاح"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir --upgrade --force-reinstall yt-dlp
RUN python -c "import yt_dlp; print('yt-dlp version:', yt_dlp.version.__version__)"

COPY . .

CMD ["python", "bot.py"]
