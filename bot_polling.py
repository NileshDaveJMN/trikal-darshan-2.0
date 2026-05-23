# bot_polling.py
import os
import sys
import time
import urllib.request
import urllib.parse
import json
from pathlib import Path

# 🌟 .env Auto-Load
_env_path = Path(__file__).parent / '.env'
if _env_path.exists():
    for _line in _env_path.read_text(encoding='utf-8').splitlines():
        _line = _line.strip()
        if _line and '=' in _line and not _line.startswith('#'):
            _k, _v = _line.split('=', 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# 🌟 Django Setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trikal_portal.settings')
import django
django.setup()

from django.contrib.auth.models import User
from core.models import UserProfile

# Bot Token — .env se
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(chat_id, text):
    """User ko Telegram par message bhejo"""
    try:
        url = f"{BASE_URL}/sendMessage"
        data = urllib.parse.urlencode({
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }).encode('utf-8')
        urllib.request.urlopen(url, data=data, timeout=10)
    except Exception as e:
        print(f"  ❌ Message send error: {e}")


def handle_start(chat_id, username, first_name):
    """
    /start command handle karo.
    username = website username jo link mein aaya
    """
    try:
        user = User.objects.get(username=username)
        profile = user.userprofile

        # Chat ID save karo
        profile.telegram_chat_id = str(chat_id)
        profile.save(update_fields=['telegram_chat_id'])

        display_name = user.first_name or user.username
        print(f"  ✅ Linked: {username} → chat_id {chat_id}")

        welcome = (
            f"🎉 *बधाई हो {display_name} जी!*\n\n"
            f"आपका त्रिकाल दर्शन अकाउंट सफलतापूर्वक Telegram से जुड़ गया है! ✨\n\n"
            f"🌅 अब आपको *रोज़ सुबह* यहाँ आपका व्यक्तिगत AI राशिफल मिलेगा।\n\n"
            f"🔮 *त्रिकाल दर्शन* पर जाएं और अपनी कुंडली देखें!"
        )
        send_message(chat_id, welcome)

    except User.DoesNotExist:
        print(f"  ❌ User '{username}' DB mein nahi mila")
        send_message(chat_id, (
            "⚠️ आपका अकाउंट नहीं मिला।\n"
            "कृपया वेबसाइट पर जाकर दोबारा 'Telegram Bot से जुड़ें' पर क्लिक करें।"
        ))
    except Exception as e:
        print(f"  ❌ handle_start error: {e}")


def handle_updates():
    """Main polling loop"""
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN नहीं मिला! .env चेक करें।")
        return

    offset = 0
    print("🔮 त्रिकाल दर्शन — Telegram Bot Start...")
    print("⏳ Users के /start का इंतज़ार है...\n")

    while True:
        try:
            url = f"{BASE_URL}/getUpdates?offset={offset}&timeout=20"
            resp = urllib.request.urlopen(url, timeout=30)
            data = json.loads(resp.read().decode('utf-8'))

            if data.get("ok") and data.get("result"):
                for update in data["result"]:
                    offset = update["update_id"] + 1

                    msg = update.get("message", {})
                    if not msg or "text" not in msg:
                        continue

                    chat_id   = str(msg["chat"]["id"])
                    text      = msg["text"].strip()
                    first_name = msg["from"].get("first_name", "")

                    print(f"📩 Message: '{text}' from chat_id={chat_id}")

                    if text.startswith("/start"):
                        parts = text.split(maxsplit=1)
                        if len(parts) > 1:
                            # /start username — website link se aaya
                            username = parts[1].strip()
                            handle_start(chat_id, username, first_name)
                        else:
                            # Seedha /start — bina username
                            send_message(chat_id, (
                                "🔮 *त्रिकाल दर्शन बॉट में स्वागत है!*\n\n"
                                "अपना अकाउंट जोड़ने के लिए कृपया वेबसाइट पर जाएं "
                                "और 'Telegram Bot से जुड़ें' बटन दबाएं।\n\n"
                                "🌐 trikaldarshan.pythonanywhere.com"
                            ))

                    elif text == "/status":
                        # User apna status check kar sake
                        try:
                            profile = UserProfile.objects.get(telegram_chat_id=chat_id)
                            send_message(chat_id, (
                                f"✅ आपका अकाउंट *{profile.user.username}* से जुड़ा है।\n"
                                f"🌅 रोज़ सुबह राशिफल मिलेगा।"
                            ))
                        except UserProfile.DoesNotExist:
                            send_message(chat_id, "❌ आपका अकाउंट लिंक नहीं है।")

        except urllib.error.URLError as e:
            print(f"  ⚠️ Network error: {e} — 5s wait...")
            time.sleep(5)
        except Exception as e:
            print(f"  ❌ Polling error: {e}")
            time.sleep(3)

        time.sleep(1)


if __name__ == "__main__":
    handle_updates()