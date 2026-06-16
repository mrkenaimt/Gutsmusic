import os
import re
import subprocess
import sys
import threading
import telebot
from telebot import types
from flask import Flask

# ====== 1. فتح سيرفر ويب مصغر لإرضاء نظام الـ Port في Render ======
app = Flask('')

@app.route('/')
def home():
    return "MIATAAA Music Bot is Alive and Running with GitHub Patch!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web_server, daemon=True).start()

# ====== 2. حل مشكلة الـ FFmpeg تلقائياً ======
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
    print("✅ FFmpeg تم تهيئته بنجاح")
except ImportError:
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "static-ffmpeg"], check=True)
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except Exception as e:
        print(f"⚠️ فشل تهيئة static-ffmpeg: {e}")

# ====== 3. تثبيت وتحديث yt-dlp مع ملحق تخطي الحظر الرسمي (POT) ======
try:
    # تحديث الأداة الأساسية
    subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "--upgrade", "yt-dlp"], check=True)
    # تثبيت ملحق تخطي Challenge يوتيوب المذكور في مجتمعات GitHub
    subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "--upgrade", "yt-dlp-get-pot"], check=True)
    print("✅ تم تثبيت حزمة yt-dlp-get-pot بنجاح لتخطي الحظر")
except Exception as _e:
    print(f"⚠️ فشل تثبيت ملحقات التخطي: {_e}")

import yt_dlp

# ====== 4. إعداد البوت والتوكن الآمن ======
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise SystemExit("❌ خطأ: تأكد من ضبط متغير BOT_TOKEN في إعدادات Render")

bot = telebot.TeleBot(BOT_TOKEN)

DOWNLOAD_DIR = 'downloads'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# الإعدادات الموصى بها في الـ GitHub لتجاوز البوت ديتكشن
ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'quiet': True,
    'nocheckcertificate': True,
    'prefer_insecure': True,
    # تفعيل بروتوكول IOS والـ Web Client المحدث بدلاً من الأندرويد لثبات التوكن
    'extractor_args': {
        'youtube': {
            'player_client': ['ios', 'web'],
            'skip': ['dash', 'hls']
        }
    }
}

# ====== أمر /start ======
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "✨ *welcome to MIATAAA music* ✨\n\nTHIS ONLY FOR U MOMMY 😩 🚀\n\nDEV : @mrkenai",
        parse_mode="Markdown"
    )

# ====== الاستماع للبحث والتحميل المباشر مع تطبيق الباتش ======
@bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'))
def direct_download(message):
    query = message.text
    chat_id = message.chat.id
    
    msg = bot.send_message(chat_id, f"🔍 *جاري معالجة الطلب وتخطي الحظر لـ: {query}...*", parse_mode="Markdown")

    try:
        # استخدام البحث عن أول نتيجة مباشرة
        url = f"ytsearch1:{query}"
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if 'entries' in info and info['entries']:
                actual_info = info['entries'][0]
            else:
                actual_info = info
                
            filename = ydl.prepare_filename(actual_info)
            mp3_filename = os.path.splitext(filename)[0] + '.mp3'
            title = actual_info.get('title', query)

        try:
            bot.delete_message(chat_id, msg.message_id)
        except Exception:
            pass

        if os.path.exists(mp3_filename):
            with open(mp3_filename, 'rb') as audio:
                bot.send_audio(
                    chat_id, audio,
                    title=title,
                    performer="MIATAAA",
                    caption=f"✨ تم التحميل بنجاح بعد تخطي القيود\n🎵 {title}"
                )
            os.remove(mp3_filename)
        else:
            actual_file = filename if os.path.exists(filename) else None
            if actual_file:
                with open(actual_file, 'rb') as audio:
                    bot.send_audio(chat_id, audio, title=title, performer="MIATAAA")
                os.remove(actual_file)
            else:
                raise FileNotFoundError("الملف الصوتي مفقود.")

    except Exception as e:
        try:
            bot.delete_message(chat_id, msg.message_id)
        except Exception:
            pass
        bot.send_message(chat_id, "⚠️ يوتيوب يفرض قيوداً معقدة حالياً، جرب اسماً آخر أو أعد المحاولة.")
        print(f"🔥 Error logged: {e}")


print("🚀 تم تشغيل البيئة بالباتش الموصى به من مجتمع المطورين...")
bot.polling(none_stop=True, interval=1, skip_pending=True)
