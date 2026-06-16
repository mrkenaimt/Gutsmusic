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
    return "MIATAAA Music Bot is Alive and Running 24/7!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web_server, daemon=True).start()

# ====== 2. حل مشكلة الـ FFmpeg للاستضافات السحابية تلقائياً ======
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

# ====== 3. تحديث أداة yt-dlp تلقائياً لضمان استقرار التحميل ======
try:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-cache-dir", "--upgrade", "yt-dlp"],
        check=True, timeout=60
    )
except Exception as _e:
    print(f"⚠️ تحديث yt-dlp فشل: {_e}")

import yt_dlp
print(f"✅ yt-dlp version: {yt_dlp.version.__version__}")

# ====== 4. إعداد البوت والتوكن الآمن ======
BOT_TOKEN = os.environ.get('BOT_TOKEN')

if not BOT_TOKEN:
    raise SystemExit("❌ خطأ: تأكد من ضبط متغير BOT_TOKEN في إعدادات Render")

bot = telebot.TeleBot(BOT_TOKEN)

DOWNLOAD_DIR = 'downloads'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# 🔥 الإعدادات السحرية لتخطي الحظر عبر محاكاة عملاء الأندرويد والتلفاز الذكي
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
    # الخدعة هنا: نحدد لـ yt-dlp أن يستعمل بروتوكولات الأجهزة الذكية المتسامحة مع الـ IPs السحابية
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'ios', 'tvhtml5'],
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

# ====== البحث والتحميل الفوري المباشر والدقيق بنسبة 100% ======
@bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'))
def direct_download(message):
    query = message.text
    chat_id = message.chat.id
    
    msg = bot.send_message(chat_id, f"🔍 *جاري البحث والتحميل المباشر لـ: {query}...*", parse_mode="Markdown")

    try:
        # البحث المباشر عن أول نتيجة مطابقة تماماً في يوتيوب بالاعتماد على عميل الأندرويد
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

        # حذف رسالة الانتظار
        try:
            bot.delete_message(chat_id, msg.message_id)
        except Exception:
            pass

        # إرسال الملف الصوتي فوراً للمستخدم
        if os.path.exists(mp3_filename):
            with open(mp3_filename, 'rb') as audio:
                bot.send_audio(
                    chat_id, audio,
                    title=title,
                    performer="MIATAAA",
                    caption=f"✨ تم التحميل بنجاح عبر MIATAAA\n🎵 {title}"
                )
            os.remove(mp3_filename)
        else:
            actual_file = filename if os.path.exists(filename) else None
            if actual_file:
                with open(actual_file, 'rb') as audio:
                    bot.send_audio(chat_id, audio, title=title, performer="MIATAAA")
                os.remove(actual_file)
            else:
                raise FileNotFoundError("المصنف الصوتي غير موجود.")

    except Exception as e:
        try:
            bot.delete_message(chat_id, msg.message_id)
        except Exception:
            pass
        bot.send_message(chat_id, "⚠️ يوتيوب قام بحظر الطلب مجدداً. السيرفرات المجانية تواجه قيوداً صارمة اليوم.")
        print(f"🔥 Error during execution: {e}")


print("🚀 تم تفعيل نظام محاكاة الأندرويد والتلفاز الذكي وتصفية القوائم...")
bot.polling(none_stop=True, interval=1, skip_pending=True)
        
