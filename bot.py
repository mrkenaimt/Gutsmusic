import os
import re
import subprocess
import sys
import threading
import telebot
from telebot import types
import requests
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

# إعدادات تحميل الصوت المستقرة من يوتيوب
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
    'extractor_args': {'youtube': {'skip': ['dash', 'hls']}}
}

LRCLIB_HEADERS = {'User-Agent': 'MIATAA-Bot/1.0 (https://t.me/mrkenai)'}


# ====== دالة جلب كلمات الأغاني ======
def fetch_lyrics(title, duration=0):
    clean = title.lower()
    clean = re.sub(r'\(official.*?\)|\[.*?\]', '', clean)
    clean = re.sub(r'\b(video|audio|music|clip|lyric|lyrics|hd|4k|mv)\b', '', clean)
    clean = re.sub(r'\bft\..*|\bfeat\..*', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()

    try:
        url = f"https://lrclib.net/api/search?q={requests.utils.quote(clean)}"
        r = requests.get(url, headers=LRCLIB_HEADERS, timeout=10)
        if r.status_code == 200:
            results = r.json()
            if results:
                lyrics = results[0].get('plainLyrics') or results[0].get('syncedLyrics', '')
                if lyrics:
                    lyrics = re.sub(r'\[\d+:\d+\.\d+\]', '', lyrics).strip()
                    return lyrics
    except Exception:
        pass
    return None


# ====== أمر /start ======
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "✨ *welcome to MIATAA music* ✨\n\nTHIS ONLY FOR U MOMMY 😩 🚀\n\nDEV : @mrkenai",
        parse_mode="Markdown"
    )


# ====== البحث المباشر السريع والخالي من الحظر ======
@bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'))
def auto_search(message):
    query = message.text
    msg = bot.send_message(message.chat.id, "🔍 *جاري البحث الآمن...*", parse_mode="Markdown")

    try:
        # البحث يتم باستخدام سيرفر yt-dlp الداخلي للنتائج العامة السريعة
        safe_search_opts = {'quiet': True, 'default_search': 'ytsearch5', 'nocheckcertificate': True}
        
        with yt_dlp.YoutubeDL(safe_search_opts) as ydl:
            # نستخرج البيانات فقط بدون تحميل لتفادي الحظر
            info = ydl.extract_info(f"ytsearch5:{query}", download=False)
            results = info.get('entries', [])

        try:
            bot.delete_message(message.chat.id, msg.message_id)
        except Exception:
            pass

        if not results:
            return bot.send_message(message.chat.id, "❌ لم أجد نتائج لهذه الأغنية.")

        markup = types.InlineKeyboardMarkup()
        for r in results[:5]:
            track_id = r.get('id')
            track_title = r.get('title', 'Audio')
            if track_id:
                markup.add(types.InlineKeyboardButton(
                    text=f"🎵 {track_title[:40]}",
                    callback_data=f"dl|{track_id}"
                ))

        bot.send_message(
            message.chat.id,
            "✨ *Here is what u ask for princess:*",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    except Exception as e:
        try:
            bot.delete_message(message.chat.id, msg.message_id)
        except Exception:
            pass
        bot.send_message(message.chat.id, "⚠️ حدث خطأ أثناء جلب النتائج.")
        print(f"Search Error: {e}")


# ====== معالجة الأزرار (التحميل المباشر الآمن) ======
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    chat_id = call.message.chat.id
    data = call.data

    if data.startswith("dl|"):
        track_id = data.split("|", 1)[1]
        msg = bot.send_message(chat_id, "📥 *جاري سحب وتجهيز الملف من السيرفر المباشر...*", parse_mode="Markdown")

        try:
            # التحميل المباشر والآمن برابط الفيديو من يوتيوب لتخطي الـ DRM
            url = f"https://www.youtube.com/watch?v={track_id}"
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                mp3_filename = os.path.splitext(filename)[0] + '.mp3'
                title = info.get('title', 'Audio')
                duration = info.get('duration', 0)

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(
                "🎤 LYRICS",
                callback_data=f"lyr|{track_id[:20]}|{int(duration)}"
            ))

            if os.path.exists(mp3_filename):
                with open(mp3_filename, 'rb') as audio:
                    bot.send_audio(
                        chat_id, audio,
                        title=title,
                        performer="MIATAAA",
                        caption=f"✨ تم التحميل عبر MIATAAA\n🎵 {title}",
                        reply_markup=markup
                    )
                os.remove(mp3_filename)
            else:
                actual_file = filename if os.path.exists(filename) else None
                if actual_file:
                    with open(actual_file, 'rb') as audio:
                        bot.send_audio(chat_id, audio, title=title, performer="MIATAAA", reply_markup=markup)
                    os.remove(actual_file)
                else:
                    raise FileNotFoundError("الملف الصوتي مفقود.")

            try:
                bot.delete_message(chat_id, msg.message_id)
            except Exception:
                pass

        except Exception as e:
            try:
                bot.delete_message(chat_id, msg.message_id)
            except Exception:
                pass
            bot.send_message(chat_id, "⚠️ حدث خطأ أثناء التحميل. يرجى تجربة أغنية أخرى.")
            print(f"Download Error: {e}")

    elif data.startswith("lyr|"):
        parts = data.split("|")
        duration = int(parts[2]) if len(parts) > 2 else 0
        video_title = call.message.caption if call.message.caption else ""
        video_title = video_title.replace("✨ تم التحميل عبر MIATAAA\n🎵 ", "")

        msg = bot.send_message(chat_id, "⏳ *جاري جلب الكلمات...*", parse_mode="Markdown")

        try:
            clean_title = video_title.lower()
            clean_title = re.sub(r'\(official.*?\)|\[.*?\]', '', clean_title)
            clean_title = re.sub(r'\b(video|audio|music|clip|lyric|lyrics)\b', '', clean_title)
            clean_title = re.sub(r'\s+', ' ', clean_title).strip()

            lyrics = fetch_lyrics(clean_title, duration)
            
            try:
                bot.delete_message(chat_id, msg.message_id)
            except Exception:
                pass

            if lyrics:
                bot.send_message(chat_id, f"🎤 LYRICS\n\n{lyrics[:4000]}")
            else:
                bot.send_message(chat_id, f"❌ لم أجد كلمات لـ:\n{clean_title}")

        except Exception as e:
            try:
                bot.delete_message(chat_id, msg.message_id)
            except Exception:
                pass
            bot.send_message(chat_id, "⚠️ عذراً، حدث مشكل أثناء جلب الكلمات.")


print("✅ البوت مستقر بالكامل وجاهز للعمل...")
bot.polling(none_stop=True, interval=1, skip_pending=True)
                    
