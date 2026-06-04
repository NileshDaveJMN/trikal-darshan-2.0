# core/views/telegram_webhook_view.py
"""
Telegram Webhook View
- Koi always-on task nahi chahiye
- Free PythonAnywhere plan mein kaam karta hai
- Jab bhi user /start kare, Telegram seedha is URL ko call karta hai
"""

import json
import os
import requests
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from core.models import UserProfile

# .env load karo
_env = Path(__file__).parent.parent.parent / '.env'
if _env.exists():
    for _line in _env.read_text(encoding='utf-8').splitlines():
        _line = _line.strip()
        if _line and '=' in _line and not _line.startswith('#'):
            _k, _v = _line.split('=', 1)
            os.environ.setdefault(_k.strip(), _v.strip())

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


def send_message(chat_id, text):
    """Telegram par message bhejo"""
    if not BOT_TOKEN:
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }, timeout=10, verify=False)
    except Exception as e:
        print(f"Telegram send error: {e}")


@csrf_exempt
def telegram_webhook(request):
    """
    Telegram Webhook endpoint.
    URL: /telegram-webhook/
    """
    if request.method != "POST":
        return JsonResponse({"status": "ok"})

    try:
        data = json.loads(request.body.decode("utf-8"))
        message = data.get("message", {})

        if not message or "text" not in message:
            return JsonResponse({"status": "no message"})

        chat_id   = str(message["chat"]["id"])
        text      = message["text"].strip()
        first_name = message.get("from", {}).get("first_name", "")

        print(f"📩 Webhook: '{text}' from {chat_id}")

        if text.startswith("/start"):
            parts = text.split(maxsplit=1)

            if len(parts) > 1:
                # /start username — website button se aaya
                username = parts[1].strip()
                try:
                    user = User.objects.get(username=username)
                    profile = user.userprofile
                    profile.telegram_chat_id = chat_id
                    profile.save(update_fields=["telegram_chat_id"])

                    display = user.first_name or user.username
                    print(f"✅ Linked: {username} → {chat_id}")

                    send_message(chat_id, (
                        f"🎉 *बधाई हो {display} जी!*\n\n"
                        f"आपका त्रिकाल दर्शन अकाउंट Telegram से जुड़ गया! ✨\n\n"
                        f"🌅 अब आपको *रोज़ सुबह* यहाँ आपका व्यक्तिगत AI राशिफल मिलेगा।\n\n"
                        f"🔮 शुभ दिन! 🙏"
                    ))

                except User.DoesNotExist:
                    print(f"❌ User '{username}' nahi mila")
                    send_message(chat_id, (
                        "⚠️ आपका अकाउंट नहीं मिला।\n"
                        "कृपया वेबसाइट पर जाएं और 'Telegram Bot से जुड़ें' बटन दोबारा दबाएं।"
                    ))
            else:
                # Seedha /start — bina username
                send_message(chat_id, (
                    "🔮 *त्रिकाल दर्शन बॉट में स्वागत है!*\n\n"
                    "अपना अकाउंट जोड़ने के लिए कृपया वेबसाइट पर जाएं "
                    "और 'Telegram Bot से जुड़ें' बटन दबाएं।\n\n"
                    "🌐 https://trikal-darshan.onrender.com"
                ))

        elif text == "/status":
            try:
                profile = UserProfile.objects.get(telegram_chat_id=chat_id)
                send_message(chat_id, (
                    f"✅ आपका अकाउंट *{profile.user.username}* से जुड़ा है।\n"
                    f"🌅 रोज़ सुबह राशिफल मिलेगा।"
                ))
            except UserProfile.DoesNotExist:
                send_message(chat_id, "❌ आपका अकाउंट लिंक नहीं है।")

    except Exception as e:
        print(f"Webhook error: {e}")

    return JsonResponse({"status": "ok"})
