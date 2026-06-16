import os
import re
import subprocess
import sys
import telebot
from telebot import types
import requests

# ====== 1. حل مشكلة الـ FFmpeg للاستضافات السحابية تلقائياً ======
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
    print("✅ FFmpeg تم تهيئته بنجاح عبر static-ffmpeg")
except ImportError:
    try:
        # إذا لم تكن المكتبة مثبتة في البيئة، يتم تحميلها وإعدادها فوراً
        subprocess.run([sys.executable, "-m", "pip", "install", "static-ffmpeg"], check=True)
        import static_ffmpeg
        static_ffmpeg.add_paths()
        print("✅ تم تثبيت وتهيئة static-ffmpeg تلقائياً")
    except Exception as e:
        print(f"⚠️ فشل تهيئة static-ffmpeg: {e}")

# ====== 2. تحديث yt-dlp تلقائياً عند بدء التشغيل ======
try:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-cache-dir", "--upgrade", "yt-dlp"],
        check=True, timeout=60
    )
except Exception as _e:
    print(f"⚠️ تحديث yt-dlp فشل: {_e}")

import yt_dlp
print(f"✅ yt-dlp version: {yt_dlp.version.__version__}")

# جلب توكن البوت من المتغيرات البيئية للمنصة المستضيفة لحمايته
BOT_TOKEN = os.environ.get('BOT_TOKEN')

if not BOT_TOKEN:
    raise SystemExit("❌ تأكدي من ضبط BOT_TOKEN في Variables على المنصة السحابية")

bot = telebot.TeleBot(BOT_TOKEN)

DOWNLOAD_DIR = 'downloads'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# ====== إعدادات yt-dlp المستقرة مع إضافة فلاتر الشهادات السحابية ======
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

search_opts = {'quiet': True, 'default_search': 'ytsearch10', 'nocheckcertificate': True}
info_opts = {'quiet': True, 'nocheckcertificate': True}

if os.path.exists('cookies.txt'):
    ydl_opts['cookiefile'] = 'cookies.txt'
    search_opts['cookiefile'] = 'cookies.txt'
    info_opts['cookiefile'] = 'cookies.txt'

LRCLIB_HEADERS = {'User-Agent': 'MIATAA-Bot/1.0 (https://t.me/mrkenai)'}


# ====== جلب الكلمات عبر lrclib.net ======
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


# ====== /start ======
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "✨ *welcome to MIATAA music* ✨\n\nTHIS ONLY FOR U MOMMY 😩 🚀\n\nDEV : @mrkenai",
        parse_mode="Markdown"
    )


# ====== البحث المباشر بالرسالة ======
@bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'))
def auto_search(message):
    query = message.text
    msg = bot.send_message(message.chat.id, "🔍 *جاري البحث...*", parse_mode="Markdown")

    try:
        with yt_dlp.YoutubeDL(search_opts) as ydl:
            info = ydl.extract_info(f"ytsearch10:{query}", download=False)
            results = info.get('entries', [])

        try:
            bot.delete_message(message.chat.id, msg.message_id)
        except Exception:
            pass

        if not results:
            return bot.send_message(message.chat.id, "❌ لم أجد نتائج.")

        markup = types.InlineKeyboardMarkup()
        for r in results[:5]:
            markup.add(types.InlineKeyboardButton(
                text=f"🎵 {r['title'][:40]}",
                callback_data=f"dl|{r['id']}"
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
        bot.send_message(message.chat.id, "⚠️ حدث خطأ أثناء البحث.")
        print(f"Search Error: {e}")


# ====== معالجة الأزرار ======
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    chat_id = call.message.chat.id
    data = call.data

    # --- تحميل MP3 ---
    if data.startswith("dl|"):
        vid = data.split("|", 1)[1]
        msg = bot.send_message(chat_id, "📥 *جاري سحب الملف...*", parse_mode="Markdown")

        try:
            url = f"https://www.youtube.com/watch?v={vid}"
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                mp3_filename = os.path.splitext(filename)[0] + '.mp3'
                title = info.get('title', 'Audio')
                duration = info.get('duration', 0)

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(
                "🎤 LYRICS",
                callback_data=f"lyr|{vid}|{int(duration)}"
            ))

            # التحقق من وجود ملف MP3 بعد انتهاء معالجة الـ FFmpeg[span_4](start_span)[span_4](end_span)
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
                # حل احتياطي إذا فشل الـ codec الصوتي وحُفظ الملف بامتداده الأساسي (m4a/webm)
                actual_file = filename if os.path.exists(filename) else None
                if actual_file:
                    with open(actual_file, 'rb') as audio:
                        bot.send_audio(chat_id, audio, title=title, performer="MIATAAA", reply_markup=markup)
                    os.remove(actual_file)
                else:
                    raise FileNotFoundError("تعذر تحديد موقع الملف الصوتي المحمل.")

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
        vid = parts[1]
        duration = int(parts[2]) if len(parts) > 2 else 0

        msg = bot.send_message(chat_id, "⏳ *جاري جلب الكلمات...*", parse_mode="Markdown")

        try:
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
                video_title = info.get('title', '')
                if not duration:
                    duration = info.get('duration', 0)

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

    # --- المزيد من النتائج ---
    elif data.startswith("more_"):
        query = data.split("_", 1)[1]
        msg = bot.send_message(chat_id, "🔄 *جاري جلب المزيد...*", parse_mode="Markdown")

        try:
            with yt_dlp.YoutubeDL(search_opts) as ydl:
                info = ydl.extract_info(f"ytsearch10:{query}", download=False)
                results = info.get('entries', [])

            try:
                bot.delete_message(chat_id, msg.message_id)
            except Exception:
                pass

            if len(results) > 5:
                markup = types.InlineKeyboardMarkup()
                for r in results[5:10]:
                    markup.add(types.InlineKeyboardButton(
                        text=f"🎵 {r['title'][:40]}",
                        callback_data=f"dl|{r['id']}"
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


print("✅ البوت شغال...")
bot.polling(none_stop=True, interval=1, skip_pending=True)
