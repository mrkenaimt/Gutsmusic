import os
import re
import telebot
from telebot import types
import yt_dlp
import requests

BOT_TOKEN = os.environ.get('BOT_TOKEN')
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')

if not BOT_TOKEN or not YOUTUBE_API_KEY:
    raise SystemExit("❌ تأكدي من ضبط BOT_TOKEN و YOUTUBE_API_KEY في Variables على Railway")

bot = telebot.TeleBot(BOT_TOKEN)

DOWNLOAD_DIR = 'downloads'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

YDL_DOWNLOAD_OPTS = {
    'format': 'bestaudio/best/bestaudio[ext=m4a]/bestaudio[ext=webm]/worstaudio',
    'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'quiet': True,
    'no_warnings': True,
    'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'web', 'mweb', 'tv']}},
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36',
    },
}

if os.path.exists('cookies.txt'):
    YDL_DOWNLOAD_OPTS['cookiefile'] = 'cookies.txt'

LRCLIB_HEADERS = {'User-Agent': 'MIATAA-Bot/1.0 (https://t.me/mrkenai)'}


# ====== البحث عبر YouTube Data API v3 ======
def youtube_search(query, max_results=10):
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        'part': 'snippet',
        'q': query,
        'type': 'video',
        'maxResults': max_results,
        'key': YOUTUBE_API_KEY,
        'videoCategoryId': '10',
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    items = r.json().get('items', [])
    results = []
    for item in items:
        vid_id = item['id']['videoId']
        title = item['snippet']['title']
        # نظّف HTML entities من العنوان
        title = title.replace('&#39;', "'").replace('&amp;', '&').replace('&quot;', '"')
        results.append({'id': vid_id, 'title': title})
    return results


# ====== جلب مدة الفيديو من YouTube API ======
def get_video_info(vid_id):
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {'part': 'snippet,contentDetails', 'id': vid_id, 'key': YOUTUBE_API_KEY}
    r = requests.get(url, params=params, timeout=10)
    items = r.json().get('items', [])
    if not items:
        return '', 0
    title = items[0]['snippet']['title']
    title = title.replace('&#39;', "'").replace('&amp;', '&').replace('&quot;', '"')
    # تحويل ISO 8601 duration لثواني
    duration_str = items[0]['contentDetails']['duration']
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
    h = int(match.group(1) or 0)
    m = int(match.group(2) or 0)
    s = int(match.group(3) or 0)
    duration = h * 3600 + m * 60 + s
    return title, duration


# ====== جلب الكلمات عبر lrclib.net ======
def fetch_lyrics(title, duration=0):
    clean = title.lower()
    clean = re.sub(r'\(official.*?\)|\[.*?\]', '', clean)
    clean = re.sub(r'\b(video|audio|music|clip|lyric|lyrics|hd|4k|mv)\b', '', clean)
    clean = re.sub(r'\bft\..*|\bfeat\..*', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()

    # خطة أ: search بالعنوان كله
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

    # خطة ب: تقسيم فنان + أغنية
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


# ====== البحث التلقائي ======
@bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'))
def auto_search(message):
    query = message.text
    msg = bot.send_message(message.chat.id, "🔍 *جاري البحث...*", parse_mode="Markdown")

    try:
        results = youtube_search(query, max_results=10)
        bot.delete_message(message.chat.id, msg.message_id)

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
        bot.send_message(message.chat.id, f"⚠️ خطأ:\n`{str(e)[:200]}`", parse_mode="Markdown")


# ====== معالجة الأزرار ======
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    chat_id = call.message.chat.id
    data = call.data

    # --- تحميل MP3 ---
    if data.startswith("dl|"):
        vid = data.split("|", 1)[1]
        msg = bot.send_message(chat_id, "📥 *جاري التحميل...*", parse_mode="Markdown")

        try:
            # نجيب العنوان والمدة من API قبل التحميل
            video_title, duration = get_video_info(vid)

            url = f"https://www.youtube.com/watch?v={vid}"
            with yt_dlp.YoutubeDL(YDL_DOWNLOAD_OPTS) as ydl:
                ydl.extract_info(url, download=True)
                filename = os.path.join(DOWNLOAD_DIR, f"{vid}.mp3")

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(
                "🎤 LYRICS",
                callback_data=f"lyr|{vid}|{int(duration)}"
            ))

            with open(filename, 'rb') as audio:
                bot.send_audio(
                    chat_id, audio,
                    title=video_title,
                    performer="MIATAAA",
                    caption=f"✨ *تم التحميل عبر MIATAAA*\n🎵 `{video_title}`",
                    reply_markup=markup,
                    parse_mode="Markdown"
                )

            bot.delete_message(chat_id, msg.message_id)
            if os.path.exists(filename):
                os.remove(filename)

        except Exception as e:
            try:
                bot.delete_message(chat_id, msg.message_id)
            except Exception:
                pass
            bot.send_message(chat_id, f"❌ خطأ في التحميل:\n`{str(e)[:200]}`", parse_mode="Markdown")

    # --- جلب الكلمات ---
    elif data.startswith("lyr|"):
        parts = data.split("|")
        vid = parts[1]
        duration = int(parts[2]) if len(parts) > 2 else 0

        msg = bot.send_message(chat_id, "⏳ *جاري جلب الكلمات...*", parse_mode="Markdown")

        try:
            video_title, dur = get_video_info(vid)
            if dur > 0:
                duration = dur

            lyrics = fetch_lyrics(video_title, duration)
            bot.delete_message(chat_id, msg.message_id)

            if lyrics:
                bot.send_message(chat_id, f"🎤 *LYRICS*\n\n{lyrics[:4000]}", parse_mode="Markdown")
            else:
                bot.send_message(chat_id, f"❌ لم أجد كلمات لـ:\n`{video_title[:100]}`", parse_mode="Markdown")

        except Exception as e:
            try:
                bot.delete_message(chat_id, msg.message_id)
            except Exception:
                pass
            bot.send_message(chat_id, f"⚠️ خطأ:\n`{str(e)[:200]}`", parse_mode="Markdown")

    # --- المزيد من النتائج ---
    elif data.startswith("more_"):
        query = data.split("_", 1)[1]
        msg = bot.send_message(chat_id, "🔄 *جاري جلب المزيد...*", parse_mode="Markdown")

        try:
            results = youtube_search(query, max_results=10)
            bot.delete_message(chat_id, msg.message_id)

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
            bot.send_message(chat_id, f"⚠️ خطأ:\n`{str(e)[:200]}`", parse_mode="Markdown")


print("✅ البوت شغال...")
bot.polling(none_stop=True, interval=1)
