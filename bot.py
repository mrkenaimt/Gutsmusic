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
    # Render يمرر الـ Port تلقائياً في متغير بيئي اسمه PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# تشغيل سيرفر الويب في Thread مستقل ليعمل بالتوازي مع البوت
threading.Thread(target=run_web_server, daemon=True).start()

# ====== 2. حل مشكلة الـ FFmpeg للاستضافات السحابية تلقائياً ======
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
    print("✅ FFmpeg تم تهيئته بنجاح عبر static-ffmpeg")
except ImportError:
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "static-ffmpeg"], check=True)
        import static_ffmpeg
        static_ffmpeg.add_paths()
        print("✅ تم تثبيت وتهيئة static-ffmpeg تلقائياً")
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
# جلب التوكن من إعدادات البيئة (Environment Variables) لحمايته ومنع التداخل
BOT_TOKEN = os.environ.get('BOT_TOKEN')

if not BOT_TOKEN:
    raise SystemExit("❌ خطأ: تأكد من ضبط متغير BOT_TOKEN في إعدادات Render")

bot = telebot.TeleBot(BOT_TOKEN)

DOWNLOAD_DIR = 'downloads'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# إعدادات تحميل الصوت المستقرة
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
    'prefer_insecure': True
}

info_opts = {'quiet': True, 'nocheckcertificate': True}
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

    words = clean.split()
    for split_at in range(1, min(5, len(words))):
        artist = ' '.join(words[:split_at])
        track = ' '.join(words[split_at:])
        if not track:
            continue
        try:
            params = f"artist_name={requests.utils.quote(artist)}&track_name={requests.utils.quote(track)}"
            if duration > 0:
                params += f"&duration={duration}"
            r = requests.get(f"https://lrclib.net/api/get?{params}", headers=LRCLIB_HEADERS, timeout=10)
            if r.status_code == 200:
                data = r.json()
                lyrics = data.get('plainLyrics') or data.get('syncedLyrics', '')
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


# ====== البحث المباشر المطور لتجاوز حظر يوتيوب للـ IP في Render ======
@bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'))
def auto_search(message):
    query = message.text
    msg = bot.send_message(message.chat.id, "🔍 *جاري البحث الآمن...*", parse_mode="Markdown")

    try:
        # البحث يتم عبر خيار SoundCloud لتفادي الـ Block تماماً
        safe_search_opts = {'quiet': True, 'default_search': 'scsearch5', 'nocheckcertificate': True}
        
        with yt_dlp.YoutubeDL(safe_search_opts) as ydl:
            info = ydl.extract_info(f"scsearch5:{query}", download=False)
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
                
        markup.add(types.InlineKeyboardButton(
            text="➕ More tracks",
            callback_data=f"more_{query[:20]}"
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


# ====== معالجة الأزرار (التحميل وعرض الكلمات) ======
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    chat_id = call.message.chat.id
    data = call.data

    # --- معالجة التحميل ---
    if data.startswith("dl|"):
        track_id = data.split("|", 1)[1]
        msg = bot.send_message(chat_id, "📥 *جاري سحب وتجهيز الملف...*", parse_mode="Markdown")

        try:
            # التحميل المباشر من المعرف المستخرج بنجاح
            url = f"https://soundcloud.com/{track_id}" if "/" in track_id else track_id
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
            bot.send_message(chat_id, "⚠️ حدث خطأ أثناء تحميل أو إرسال الأغنية.")
            print(f"Download Error: {e}")

    # --- جلب الكلمات ---
    elif data.startswith("lyr|"):
        parts = data.split("|")
        duration = int(parts[2]) if len(parts) > 2 else 0
        
        # نأخذ نص عنوان الرسالة للبحث عن الكلمات
        video_title = call.message.caption if call.message.caption else ""
        video_title = video_title.replace("✨ تم التحميل عبر MIATAAA\n🎵 ", "")

        msg = bot.send_message(chat_id, "⏳ *جاري جلب الكلمات...*", parse_mode="Markdown")

        try:
            clean_title = video_title.lower()
            clean_title = re.sub(r'\(official.*?\)|\[.*?\]', '', clean_title)
            clean_title = re.sub(r'\b(video|audio|music|clip|lyric|lyrics)\b', '', clean_title)
            clean_title = re.sub(r'\bft\..*|\bfeat\..*', '', clean_title)
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
            print(f"Lyrics Error: {e}")

    # --- جلب المزيد من النتائج ---
    elif data.startswith("more_"):
        query = data.split("_", 1)[1]
        msg = bot.send_message(chat_id, "🔄 *جاري جلب المزيد...*", parse_mode="Markdown")

        try:
            safe_search_opts = {'quiet': True, 'default_search': 'scsearch10', 'nocheckcertificate': True}
            with yt_dlp.YoutubeDL(safe_search_opts) as ydl:
                info = ydl.extract_info(f"scsearch10:{query}", download=False)
                results = info.get('entries', [])

            try:
                bot.delete_message(chat_id, msg.message_id)
            except Exception:
                pass

            if len(results) > 5:
                markup = types.InlineKeyboardMarkup()
                for r in results[5:10]:
                    track_id = r.get('id')
                    if track_id:
                        markup.add(types.InlineKeyboardButton(
                            text=f"🎵 {r.get('title', 'Audio')[:40]}",
                            callback_data=f"dl|{track_id}"
                        ))
                bot.send_message(chat_id, "➕ *إليك المزيد:*", reply_markup=markup, parse_mode="Markdown")
            else:
                bot.send_message(chat_id, "❌ لا توجد نتائج إضافية.")

        except Exception as e:
            try:
                bot.delete_message(chat_id, msg.message_id)
            except Exception:
                pass
            bot.send_message(chat_id, "⚠️ حدث خطأ أثناء جلب المزيد.")
            print(f"More Error: {e}")


print("✅ البوت مستقر وجاهز للعمل بدون حظر...")
bot.polling(none_stop=True, interval=1, skip_pending=True)
            
