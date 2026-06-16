# build-trigger-2026-06-16-1450
FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl gnupg ffmpeg && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# تأكيد إلزامي: لو node غير موجود، البناء كامل يفشل هنا (ما رح نكمل بدونه)
RUN node --version && echo "✅ Node.js مثبت بنجاح"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir --upgrade --force-reinstall yt-dlp
RUN python -c "import yt_dlp; print('yt-dlp version:', yt_dlp.version.__version__)"

COPY . .

CMD ["python", "bot.py"]
