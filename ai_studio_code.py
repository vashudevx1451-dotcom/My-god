import os
import re
import io
import time
import socket
import threading
import requests
import urllib3.util.connection as urllib3_cn
import telebot
from telebot import apihelper

# ============================================================================
# 1. TURBO IPv4 FORCE (Eliminates IPv6 timeout & makes uploads ultra-fast)
# ============================================================================
def allowed_gai_family():
    return socket.AF_INET

urllib3_cn.allowed_gai_family = allowed_gai_family

# Persistent Keep-Alive Session for Telegram API
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=32, pool_maxsize=64, max_retries=2)
session.mount("https://", adapter)
session.mount("http://", adapter)
apihelper.SESSION_TIME_TO_LIVE = None

BOT_TOKEN = (os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or os.environ.get("BOT_TOKEN", "").strip()).strip("\"' ")
MAX_RUNTIME_SECONDS = int(os.environ.get("MAX_RUNTIME_SECONDS", str(5 * 3600 + 25 * 60)))

if not BOT_TOKEN:
    print("⚠️ WARNING: BOT_TOKEN is empty! Please set BOT_TOKEN in your GitHub Secrets.")

bot = telebot.TeleBot(BOT_TOKEN or "EMPTY_TOKEN", threaded=True, num_threads=8)

# ============================================================================
# 2. CLEANER & UNICODE SANS-SERIF BOLD ENGINE
# ============================================================================
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F100-\U0001F1FF"
    "\U00013000-\U0001342F"
    "\U00012000-\U0001254F"
    "\uFE0F\u200D"
    "]+",
    flags=re.UNICODE,
)

WATERMARK_KEYWORDS = [
    "Powered by",
    "Extracted by",
    "Downloaded by",
    "Uploaded by",
    "Provided by",
    "Leaked by",
    "MadXABhi",
    "Mad X Abhi",
    "AS MULTIVERSE",
    "𓊈",
    "𓊉",
    "𒆜",
    "★",
    "⚡",
    "🔥",
]

SANS_BOLD_MAP = {
    "A": "𝗔", "B": "𝗕", "C": "𝗖", "D": "𝗗", "E": "𝗘", "F": "𝗙", "G": "𝗚",
    "H": "𝗛", "I": "𝗜", "J": "𝗝", "K": "𝗞", "L": "𝗟", "M": "𝗠", "N": "𝗡",
    "O": "𝗢", "P": "𝗣", "Q": "𝗤", "R": "𝗥", "S": "𝗦", "T": "𝗧", "U": "𝗨",
    "V": "𝗩", "W": "𝗪", "X": "𝗫", "Y": "𝗬", "Z": "𝗭",
    "a": "𝗮", "b": "𝗯", "c": "𝗰", "d": "𝗱", "e": "𝗲", "f": "𝗳", "g": "𝗴",
    "h": "𝗵", "i": "𝗶", "j": "𝗷", "k": "𝗸", "l": "𝗹", "m": "𝗺", "n": "𝗻",
    "o": "𝗼", "p": "𝗽", "q": "𝗾", "r": "𝗿", "s": "𝘀", "t": "𝘁", "u": "𝘂",
    "v": "𝘃", "w": "𝘄", "x": "𝘅", "y": "𝘆", "z": "𝘇",
    "0": "𝟬", "1": "𝟭", "2": "𝟮", "3": "𝟯", "4": "𝟰", "5": "𝟱", "6": "𝟲",
    "7": "𝟳", "8": "𝟴", "9": "𝟵",
}

def to_sans_bold(text: str) -> str:
    if not text:
        return ""
    return "".join(SANS_BOLD_MAP.get(ch, ch) for ch in text)

def remove_links_and_usernames(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"https?://\S+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"t\.me/\S+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"@\w+", "", text)
    return text.strip()

def strip_promotional_noise(text: str) -> str:
    if not text:
        return ""
    for kw in WATERMARK_KEYWORDS:
        text = re.sub(re.escape(kw) + r"[^\n]*", "", text, flags=re.IGNORECASE)
    return text.strip()

def clean_title_value(val: str) -> str:
    if not val:
        return ""
    val = re.sub(r"^(?:Title\s*:?\s*)+", "", val, flags=re.IGNORECASE).strip()
    val = remove_links_and_usernames(val)
    val = strip_promotional_noise(val)
    val = re.sub(r"\.[a-zA-Z0-9]{2,5}$", "", val).strip()
    val = re.sub(r"[_\-]+", " ", val)
    val = re.sub(r"\s+", " ", val).strip()
    return val

def clean_subject_value(val: str) -> str:
    if not val:
        return ""
    val = re.sub(r"^(?:Subject\s*:?\s*)+", "", val, flags=re.IGNORECASE).strip()
    val = remove_links_and_usernames(val)
    val = strip_promotional_noise(val)
    val = re.sub(r"\s+", " ", val).strip()
    return val

def clean_pdf_filename(raw_filename: str, extracted_title: str = "") -> tuple[str, bool]:
    if not raw_filename:
        raw_filename = f"{extracted_title}.pdf" if extracted_title else "Document.pdf"

    original = raw_filename
    name = raw_filename
    ext = ".pdf"
    m = re.search(r"(\.[a-zA-Z0-9]{2,5})$", name)
    if m:
        ext = m.group(1)
        name = name[: m.start()]

    name = remove_links_and_usernames(name)
    name = strip_promotional_noise(name)
    name = EMOJI_PATTERN.sub("", name)
    name = re.sub(r"^\[.*?\]\s*", "", name)
    name = re.sub(r"\s*\[.*?\]$", "", name)
    name = re.sub(r"[\(\)\{\}\<\>\|#\*~`!@\$%\^&+=]+", " ", name)
    name = re.sub(r"[_\-]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    if not name and extracted_title:
        name = clean_title_value(extracted_title)

    if not name:
        name = "Document"

    final_name = f"{name}{ext}"
    return final_name, (final_name != original)

def format_caption(raw_text: str, fallback_filename: str = "") -> tuple[str, str]:
    if not raw_text and not fallback_filename:
        return "", ""

    lines = [ln.strip() for ln in (raw_text or "").split("\n") if ln.strip()]
    title = ""
    subject = ""
    others = []

    for line in lines:
        cleaned_line = remove_links_and_usernames(line)
        cleaned_line = strip_promotional_noise(cleaned_line)
        cleaned_line = EMOJI_PATTERN.sub("", cleaned_line).strip()
        if not cleaned_line:
            continue

        if re.match(r"^Title\s*:", cleaned_line, re.IGNORECASE):
            raw_v = re.sub(r"^Title\s*:?\s*", "", cleaned_line, flags=re.IGNORECASE).strip()
            title = clean_title_value(raw_v)
        elif re.match(r"^Subject\s*:", cleaned_line, re.IGNORECASE):
            raw_v = re.sub(r"^Subject\s*:?\s*", "", cleaned_line, flags=re.IGNORECASE).strip()
            subject = clean_subject_value(raw_v)
        elif not title and len(lines) == 1 and not re.search(r"^[A-Za-z]+:", cleaned_line):
            title = clean_title_value(cleaned_line)
        else:
            cleaned_other = re.sub(r"\s+", " ", cleaned_line).strip()
            if cleaned_other:
                others.append(cleaned_other)

    if not title and fallback_filename:
        title = clean_title_value(fallback_filename)

    parts = []
    if title:
        parts.append(f"🔖 {to_sans_bold('Title:')} {to_sans_bold(title)}")
    if subject:
        parts.append(f"📚 {to_sans_bold('Subject:')} {subject}")
    for o in others:
        parts.append(o)

    return "\n\n".join(parts), title

RENAMED_FILE_CACHE = {}
LAST_DOC_BY_CHAT = {}

def send_renamed_pdf_fast(chat_id, file_id, file_unique_id, clean_name, caption, file_size=0):
    cache_key = f"{file_unique_id}::{clean_name}" if file_unique_id else None
    if cache_key and cache_key in RENAMED_FILE_CACHE:
        try:
            bot.send_document(chat_id, RENAMED_FILE_CACHE[cache_key], caption=caption)
            return True
        except Exception:
            RENAMED_FILE_CACHE.pop(cache_key, None)

    try:
        file_info = bot.get_file(file_id)
        dl_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        resp = session.get(dl_url, timeout=40)
        resp.raise_for_status()
        bio = io.BytesIO(resp.content)
        bio.name = clean_name

        sent = bot.send_document(
            chat_id,
            bio,
            caption=caption,
            visible_file_name=clean_name,
            timeout=40
        )
        if sent and getattr(sent, "document", None) and cache_key:
            RENAMED_FILE_CACHE[cache_key] = sent.document.file_id
        return True
    except Exception as e:
        print("send_renamed_pdf_fast error:", e)
        raise

# ============================================================================
# 3. BOT HANDLERS (Minimal Response + Single/Bulk Video & PDF Support)
# ============================================================================
@bot.message_handler(commands=["start"])
def handle_start(message):
    bot.send_message(
        message.chat.id,
        "👋 **Welcome to TeleClean Bot!**\n\n"
        "Send or forward any Video, PDF, Document, or Text.\n"
        "• Ads & promotional links removed automatically\n"
        "• Captions professionally formatted\n"
        "• Clean filenames preserved",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["name"])
def handle_name_cmd(message):
    chat_id = message.chat.id
    last_doc = LAST_DOC_BY_CHAT.get(chat_id)
    if not last_doc:
        bot.send_message(chat_id, "Send PDF first.")
        return

    arg = re.sub(r"^/name(?:@\S+)?\s*", "", message.text or "", flags=re.IGNORECASE).strip()
    if not arg:
        last_doc["awaiting"] = True
        bot.send_message(chat_id, "Send new name:")
        return

    final_name = arg if re.search(r"\.[a-z0-9]{2,5}$", arg, re.IGNORECASE) else f"{arg}{last_doc['ext']}"
    last_doc["awaiting"] = False
    send_renamed_pdf_fast(chat_id, last_doc["file_id"], last_doc["unique_id"], final_name, last_doc["caption"], last_doc.get("size", 0))

@bot.message_handler(content_types=["video", "document", "photo", "animation", "audio"])
def handle_media(message):
    chat_id = message.chat.id
    doc = message.document
    vid = message.video
    fname = doc.file_name if doc else (vid.file_name if vid else "")
    raw_caption = message.caption or (f"Title: {fname}" if fname else "")
    cleaned_caption, extracted_title = format_caption(raw_caption, fname or "")

    if doc:
        ext_m = re.search(r"(\.[a-zA-Z0-9]{2,5})$", fname or "")
        LAST_DOC_BY_CHAT[chat_id] = {
            "file_id": doc.file_id,
            "unique_id": getattr(doc, "file_unique_id", ""),
            "size": getattr(doc, "file_size", 0) or 0,
            "ext": ext_m.group(1) if ext_m else ".pdf",
            "caption": cleaned_caption,
            "awaiting": False,
        }
        clean_name, was_modified = clean_pdf_filename(fname or "", extracted_title)
        if was_modified and (not doc.file_size or doc.file_size <= 20 * 1024 * 1024):
            try:
                send_renamed_pdf_fast(chat_id, doc.file_id, getattr(doc, "file_unique_id", ""), clean_name, cleaned_caption, doc.file_size or 0)
                return
            except Exception as e:
                print("PDF rename fallback to copy_message:", e)

    bot.copy_message(
        chat_id=chat_id,
        from_chat_id=chat_id,
        message_id=message.message_id,
        caption=cleaned_caption,
    )

@bot.message_handler(content_types=["text"])
def handle_text(message):
    chat_id = message.chat.id
    txt = (message.text or "").strip()
    if not txt or txt.startswith("/"):
        return

    last_doc = LAST_DOC_BY_CHAT.get(chat_id)
    if last_doc and last_doc.get("awaiting"):
        last_doc["awaiting"] = False
        final_name = txt if re.search(r"\.[a-z0-9]{2,5}$", txt, re.IGNORECASE) else f"{txt}{last_doc['ext']}"
        send_renamed_pdf_fast(chat_id, last_doc["file_id"], last_doc["unique_id"], final_name, last_doc["caption"], last_doc.get("size", 0))
        return

    cleaned_caption, _ = format_caption(txt)
    if cleaned_caption:
        bot.send_message(chat_id, cleaned_caption)

# ============================================================================
# 4. 5-HOUR AUTO-RESTART TIMER FOR 24/7 GITHUB ACTIONS
# ============================================================================
def auto_shutdown_timer():
    time.sleep(MAX_RUNTIME_SECONDS)
    print(f"Reached {MAX_RUNTIME_SECONDS}s runtime limit. Stopping cleanly for GitHub Actions auto-restart...")
    bot.stop_polling()
    os._exit(0)

if __name__ == "__main__":
    print("🚀 Starting TeleClean Bot...")
    try:
        bot.delete_webhook(drop_pending_updates=True)
        print("✅ Webhook cleared (clean polling ready).")
    except Exception as e:
        print("Webhook notice:", e)

    try:
        me = bot.get_me()
        print(f"🤖 Connected successfully as @{me.username} ({me.first_name}) [ID: {me.id}]")
    except Exception as e:
        print(f"❌ Telegram connection failed: {e}")
        print("Please check that BOT_TOKEN in GitHub Secrets is correct and valid.")
        raise

    # Set menu commands: Only /start in the Telegram bot menu
    try:
        bot.set_my_commands([
            telebot.types.BotCommand("start", "Start Bot")
        ])
    except Exception as e:
        print("Menu command setup notice:", e)

    t = threading.Thread(target=auto_shutdown_timer, daemon=True)
    t.start()

    print("⚡ TeleClean Turbo Bot is now LIVE & listening for messages (24/7 GitHub Runner)...")
    bot.infinity_polling(timeout=20, long_polling_timeout=20, skip_pending=False)?:\S+)?\s*", "", message.text or "", flags=re.IGNORECASE).strip()
    if not arg:
        last_doc["awaiting"] = True
        bot.send_message(chat_id, "📝 Please send the new filename:")
        return

    final_name = arg if re.search(r"\.[a-z0-9]{2,5}$", arg, re.IGNORECASE) else f"{arg}{last_doc['ext']}"
    last_doc["awaiting"] = False
    send_renamed_pdf_fast(chat_id, last_doc["file_id"], last_doc["unique_id"], final_name, last_doc["caption"])

@bot.message_handler(content_types=["video", "document", "photo", "animation", "audio"])
def handle_media(message):
    chat_id = message.chat.id
    doc = message.document
    vid = message.video
    fname = doc.file_name if doc else (vid.file_name if vid else "")
    raw_caption = message.caption or (f"Title: {fname}" if fname else "")
    cleaned_caption, extracted_title = format_caption(raw_caption, fname or "")

    if doc:
        ext_m = re.search(r"(\.[a-zA-Z0-9]{2,5})$", fname or "")
        LAST_DOC_BY_CHAT[chat_id] = {
            "file_id": doc.file_id,
            "unique_id": getattr(doc, "file_unique_id", ""),
            "ext": ext_m.group(1) if ext_m else ".pdf",
            "caption": cleaned_caption,
            "awaiting": False,
        }
        clean_name, was_modified = clean_pdf_filename(fname or "", extracted_title)
        if was_modified and (not doc.file_size or doc.file_size <= 20 * 1024 * 1024):
            try:
                send_renamed_pdf_fast(chat_id, doc.file_id, getattr(doc, "file_unique_id", ""), clean_name, cleaned_caption)
                return
            except Exception as e:
                print("PDF rename fallback to copy_message:", e)

    bot.copy_message(
        chat_id=chat_id,
        from_chat_id=chat_id,
        message_id=message.message_id,
        caption=cleaned_caption,
    )

@bot.message_handler(content_types=["text"])
def handle_text(message):
    chat_id = message.chat.id
    txt = (message.text or "").strip()
    if not txt or txt.startswith("/"):
        return

    last_doc = LAST_DOC_BY_CHAT.get(chat_id)
    if last_doc and last_doc.get("awaiting"):
        last_doc["awaiting"] = False
        final_name = txt if re.search(r"\.[a-z0-9]{2,5}$", txt, re.IGNORECASE) else f"{txt}{last_doc['ext']}"
        send_renamed_pdf_fast(chat_id, last_doc["file_id"], last_doc["unique_id"], final_name, last_doc["caption"])
        return

    cleaned_caption, _ = format_caption(txt)
    if cleaned_caption:
        bot.send_message(chat_id, cleaned_caption)

# ============================================================================
# 4. 5-HOUR AUTO-RESTART TIMER FOR 24/7 GITHUB ACTIONS
# ============================================================================
def auto_shutdown_timer():
    time.sleep(MAX_RUNTIME_SECONDS)
    print(f"Reached {MAX_RUNTIME_SECONDS}s runtime limit. Stopping cleanly for GitHub Actions auto-restart...")
    bot.stop_polling()
    os._exit(0)

if __name__ == "__main__":
    # Release any previous polling lock immediately
    try:
        session.post(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook", json={"url": "https://example.com/reset"}, timeout=5)
        session.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", json={"drop_pending_updates": False}, timeout=5)
    except Exception:
        pass

    # Set menu commands: Only /start in the Telegram bot menu
    try:
        bot.set_my_commands([
            telebot.types.BotCommand("start", "Start Bot")
        ])
    except Exception as e:
        print("Menu command setup notice:", e)

    t = threading.Thread(target=auto_shutdown_timer, daemon=True)
    t.start()

    print("⚡ TeleClean Turbo Bot active (24/7 GitHub Runner Mode)...")
    bot.infinity_polling(timeout=20, long_polling_timeout=20, skip_pending=False)
