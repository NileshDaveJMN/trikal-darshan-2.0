import os
import sys
import requests
import json
import random
from datetime import date
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Django सेटअप
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trikal_portal.settings')
import django
django.setup()

from core.models import UserProfile

# 🌟 .env से कीज़ और टोकन लोड करें
raw_keys = os.getenv("GEMINI_API_KEYS", "")
GEMINI_API_KEYS = [k.strip() for k in raw_keys.split(',')] if raw_keys else []
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def send_telegram_message(chat_id, text):
    if not BOT_TOKEN:
        print("Telegram Error: BOT_TOKEN not found!")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

def generate_and_send_daily_horoscope():
    print("🔮 त्रिकाल दर्शन AI इंजन (Live Mode) शुरू हो रहा है...")
    
    if not GEMINI_API_KEYS:
        print("❌ Error: No API Keys found in .env!")
        return

    users = UserProfile.objects.exclude(telegram_chat_id__isnull=True).exclude(telegram_chat_id__exact='')
    today = date.today()

    for profile in users:
        if profile.horoscope_date == today: continue
        
        user_name = profile.user.first_name or profile.user.username
        print(f"⏳ {user_name} के लिए राशिफल बन रहा है...")

        prompt = f"""
        सुप्रभात {user_name} जी! ✨ आप एक विशेषज्ञ वैदिक ज्योतिषी हैं। 
        {user_name} का पेशा: {profile.profession or 'सामान्य'}, फोकस: {profile.primary_focus or 'करियर'}, चुनौती: {profile.current_challenge or 'रुकावटें'}।
        इनके लिए आज का 4 लाइन का प्रेरणादायक और सटीक राशिफल लिखें। कोई Markdown (**, ##) का उपयोग न करें।
        """

        # 🌟 रोटेशन लॉजिक: एक रैंडम की चुनें
        api_key = random.choice(GEMINI_API_KEYS)
        
        # मॉडल का नाम 'gemini-1.5-flash' जो स्टेबल और फास्ट है
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        try:
            response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=25, verify=False)
            if response.status_code == 200:
                res_data = response.json()
                horoscope_text = res_data['candidates'][0]['content']['parts'][0]['text']
                
                # डेटाबेस और Telegram
                profile.daily_horoscope_text = horoscope_text
                profile.horoscope_date = today
                profile.save()
                
                send_telegram_message(profile.telegram_chat_id, f"🔮 *आपका आज का राशिफल*\n\n{horoscope_text}")
                print(f"✅ {user_name} को भेज दिया!")
            else:
                print(f"❌ Error {response.status_code}: {response.text}")
        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    generate_and_send_daily_horoscope()
