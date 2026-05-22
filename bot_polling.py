# bot_polling.py
import os
import sys
import time
import urllib.request
import urllib.parse
import json

# 🌟 Django ko is script se connect karne ke liye settings
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trikal_portal.settings') # Agar settings ka naam alag ho toh badal dein

import django
django.setup()

from django.contrib.auth.models import User
from core.models import UserProfile

# Bot Token (Aapki auth_views file se liya gaya hai)
BOT_TOKEN = "8353256217:AAG58hIdMPaUypfU4fXVlU3lJGJZhZ2QN1I"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_telegram_message(chat_id, text):
    """User ko wapas confirmation message bhejne ke liye"""
    try:
        url = f"{BASE_URL}/sendMessage"
        data = urllib.parse.urlencode({'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}).encode('utf-8')
        urllib.request.urlopen(url, data=data, timeout=5)
    except Exception as e:
        print("Error sending message:", e)

def handle_updates():
    offset = 0
    print("🔮 त्रिकal दर्शन Telegram Bot Engine Start Ho Gaya Hai...")
    print("⏳ Naye users ke 'START' dabane ka intezar hai...\n")
    
    while True:
        try:
            # Telegram se naye messages check karna
            url = f"{BASE_URL}/getUpdates?offset={offset}&timeout=10"
            response = urllib.request.urlopen(url, timeout=15)
            data = json.loads(response.read().decode('utf-8'))
            
            if data.get("ok") and data.get("result"):
                for update in data["result"]:
                    offset = update["update_id"] + 1
                    
                    if "message" in update and "text" in update["message"]:
                        message = update["message"]
                        chat_id = message["chat"]["id"]
                        text = message["text"].strip()
                        
                        # 🌟 Check karein agar user ne /start dabaya hai aur sath me username hai
                        if text.startswith("/start"):
                            parts = text.split()
                            if len(parts) > 1:
                                username = parts[1] # Ye hume link se milega (?start=username)
                                
                                try:
                                    # Django database me user ko dhundna
                                    user = User.objects.get(username=username)
                                    profile = user.userprofile
                                    
                                    # Chat ID save karna
                                    profile.telegram_chat_id = str(chat_id)
                                    profile.save()
                                    
                                    print(f"✅ Success: User '{username}' connect ho gaya! Chat ID: {chat_id}")
                                    
                                    # User ko Telegram par badhai ka message bhejna
                                    welcome_text = f"🎉 *बधाई हो {user.username}!*\n\nआपका त्रिकाल दर्शन अकाउंट सफलतापूर्वक लिंक हो गया है।\n\n🌅 अब आपको रोज़ सुबह सीधे यहाँ आपका व्यक्तिगत AI राशिफल मिलना शुरू हो जाएगा।"
                                    send_telegram_message(chat_id, welcome_text)
                                    
                                except User.DoesNotExist:
                                    print(f"❌ Error: Username '{username}' database me nahi mila.")
                                    send_telegram_message(chat_id, "⚠️ त्रुटि: आपका अकाउंट डेटाबेस में नहीं मिला। कृपया वेबसाइट से दोबारा कोशिश करें।")
                            else:
                                send_telegram_message(chat_id, "🔮 *त्रिकाल दर्शन बॉट में आपका स्वागत है!*\n\nकृपया वेबसाइट पर जाकर 'Telegram Bot से जुड़ें' बटन पर क्लिक करें ताकि आपका अकाउंट लिंक हो सके।")
                                
        except Exception as e:
            print("Polling Error:", e)
            
        time.sleep(1) # Har 1 second me check karega

if __name__ == "__main__":
    handle_updates()
