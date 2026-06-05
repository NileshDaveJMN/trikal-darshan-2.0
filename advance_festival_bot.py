import os, sys, datetime, random, time
import pytz
import swisseph as swe
from pathlib import Path
import google.generativeai as genai

# ── Django Setup (For Background Tasks) ────────────────────────────────
_env_path = Path(__file__).parent / '.env'
if _env_path.exists():
    for _line in _env_path.read_text(encoding='utf-8').splitlines():
        _line = _line.strip()
        if _line and '=' in _line and not _line.startswith('#'):
            _k, _v = _line.split('=', 1)
            os.environ.setdefault(_k.strip(), _v.strip())

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trikal_portal.settings')

import django
if not django.apps.apps.ready: 
    django.setup()

from core.models import UserProfile, PushSubscription
from core.views.push_views import send_push_to_user
import requests

# अपनी festival_engine से फंक्शन इम्पोर्ट करें
from festival_engine import get_today_festivals

# ── Gemini AI Setup ───────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEYS1", "").strip()
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    
model = genai.GenerativeModel("gemini-1.5-flash")

# ── 1. कल (Tomorrow) का पंचांग निकालें ────────────────────────────────
def get_tomorrow_panchang():
    try:
        # आज के समय में 1 दिन (24 घंटे) जोड़ दें
        now = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
        tomorrow = now + datetime.timedelta(days=1)
        
        # UTC में बदलें
        dt_utc = tomorrow - datetime.timedelta(hours=5, minutes=30)
        jd_ut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute / 60.0)
        swe.set_sid_mode(swe.SIDM_LAHIRI)

        res_sun, _ = swe.calc_ut(jd_ut, swe.SUN, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
        res_moon, _ = swe.calc_ut(jd_ut, swe.MOON, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
        sun_lon = res_sun[0]
        moon_lon = res_moon[0]

        tithi_idx = int(((moon_lon - sun_lon) % 360) / 12.0)
        tithi_num = (tithi_idx % 15) + 1
        paksha = "S" if tithi_idx < 15 else "K"

        moon_sun_diff = (moon_lon - sun_lon) % 360
        days_since_amavasya = moon_sun_diff / 12.190749
        amavasya_sun_lon = (sun_lon - (days_since_amavasya * 0.9856)) % 360
        lunar_month_idx = int(amavasya_sun_lon / 30)

        return {
            "date_str": tomorrow.strftime("%d %b %Y"),
            "tithi": tithi_num,
            "paksha": paksha,
            "lunar_month": lunar_month_idx,
        }
    except Exception as e:
        print(f"❌ Panchang error: {e}")
        return None

# ── 2. AI से शानदार उपाय (Remedy) लिखवाएं ─────────────────────────────
def generate_advance_remedy(festival_name, deity):
    prompt = f"""
    You are an expert Vedic Astrologer. Tomorrow is '{festival_name}' (dedicated to Lord {deity}). 
    Write a short, personalized, and inspiring advance notification message in Hindi.
    The message should build excitement and suggest one simple, powerful remedy or preparation to do *tomorrow*.
    Use the placeholder {{name}} for the user's name.
    Keep it strictly under 4-5 lines. Use emojis.
    Example tone: "✨ प्रिय {{name}}, कल {festival_name} का पावन पर्व है! कल सुबह उठकर..."
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print("AI Error:", e)
        # अगर AI फेल हो जाए, तो बैकअप मैसेज
        return f"✨ प्रिय {{name}}, कल {festival_name} का पावन पर्व है! कल {deity} जी की आराधना अवश्य करें। 🙏"

# ── 3. Telegram पर मैसेज भेजने का फंक्शन ──────────────────────────────
def send_telegram_message(chat_id, message):
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not BOT_TOKEN or not chat_id: return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=5)
    except:
        pass

# ── 4. Main Bot Engine ───────────────────────────────────────────────
def run_advance_bot():
    print("\n" + "🔮" * 25)
    print("  ADVANCE FESTIVAL & REMEDY BOT")
    print("🔮" * 25)

    # 1. कल का पंचांग निकालें
    tomorrow_panchang = get_tomorrow_panchang()
    if not tomorrow_panchang: return

    # 2. चेक करें क्या कल कोई त्योहार है? (festival_engine का उपयोग करके)
    festivals = get_today_festivals(tomorrow_panchang)
    if not festivals:
        print(f"  ℹ️ कल ({tomorrow_panchang['date_str']}) कोई विशेष पर्व नहीं है।")
        return

    festival = festivals[0]
    print(f"  🔔 Upcoming Festival Found: {festival['emoji']} {festival['name']}")

    # 3. AI से मैसेज जनरेट करें (हम इसे एक बार जनरेट करेंगे ताकि API लिमिट खत्म न हो)
    print("  🧠 Generating AI Remedy Message...")
    ai_template = generate_advance_remedy(festival['name'], festival['deity'])
    print(f"  📝 Template Ready:\n{ai_template}\n")

    # 4. सभी यूज़र्स को भेजें
    profiles = UserProfile.objects.select_related("user").all()
    sent_push = 0
    sent_tg = 0

    for profile in profiles:
        user = profile.user
        user_name = user.first_name if user.first_name else "भक्त"
        
        # यूज़र का नाम मैसेज में डालें
        personalized_msg = ai_template.replace("{name}", user_name)
        short_preview = f"कल {festival['name']} है, अपनी विशेष तैयारी जानें! ✨"

        # A. वेब पुश नोटिफिकेशन भेजें
        subs = PushSubscription.objects.filter(user=user, is_active=True)
        if subs.exists():
            send_push_to_user(user, f"कल है {festival['name']} {festival['emoji']}", short_preview, "/?tab=view-panchang")
            sent_push += 1

        # B. Telegram पर पूरा उपाय भेजें
        if profile.telegram_chat_id:
            send_telegram_message(profile.telegram_chat_id, personalized_msg)
            sent_tg += 1

        time.sleep(0.1) # सर्वर पर एक साथ लोड न पड़े इसलिए छोटा सा ब्रेक

    print("─" * 50)
    print(f"  ✅ SUCCESS: Sent {sent_push} Web Pushes & {sent_tg} Telegram Messages.")
    print("─" * 50)

if __name__ == "__main__":
    run_advance_bot()
