import os, sys, datetime, requests, random, re, time
import swisseph as swe
import pytz
from pathlib import Path

# ── Django Setup ──────────────────────────────────────────────────────
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
django.setup()

from core.models import UserProfile, PushSubscription
from core.views.push_views import send_push_to_user

# ── Gemini Setup ──────────────────────────────────────────────────────
GEMINI_API_KEYS = []
for i in range(1, 10):
    key = os.getenv(f"GEMINI_API_KEYS{i}", "").strip()
    if key:
        GEMINI_API_KEYS.append(key)
GEMINI_MODEL = "gemini-3-flash-preview"

# ── Hindu Month Names (Sidereal Solar) ───────────────────────────────
HINDU_MONTHS = [
    "मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या",
    "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"
]

# Lunar month names (Amanta system — new moon to new moon)
LUNAR_MONTHS = [
    "चैत्र", "वैशाख", "ज्येष्ठ", "आषाढ़", "श्रावण", "भाद्रपद",
    "आश्विन", "कार्तिक", "मार्गशीर्ष", "पौष", "माघ", "फाल्गुन"
]

# ── Festival Rules Dictionary ─────────────────────────────────────────
# Format: { "festival_name": {"tithi": N, "paksha": "S/K", "lunar_month": N or None} }
# paksha: S = Shukla (bright), K = Krishna (dark)
# lunar_month: 1-12 (None means every month)
# special: for Ekadashi, Pradosh etc that repeat every month

FESTIVAL_RULES = [
    # ── Every Month ──────────────────────────────────────────────────
    {"name": "एकादशी", "emoji": "🙏", "tithi": 11, "paksha": "S",
     "month": None, "deity": "विष्णु",
     "desc": "शुक्ल एकादशी"},

    {"name": "एकादशी", "emoji": "🙏", "tithi": 11, "paksha": "K",
     "month": None, "deity": "विष्णु",
     "desc": "कृष्ण एकादशी"},

    {"name": "प्रदोष व्रत", "emoji": "🕉️", "tithi": 13, "paksha": "S",
     "month": None, "deity": "शिव",
     "desc": "शुक्ल प्रदोष"},

    {"name": "प्रदोष व्रत", "emoji": "🕉️", "tithi": 13, "paksha": "K",
     "month": None, "deity": "शिव",
     "desc": "कृष्ण प्रदोष"},

    {"name": "पूर्णिमा", "emoji": "🌕", "tithi": 15, "paksha": "S",
     "month": None, "deity": "चंद्र",
     "desc": "पूर्णिमा"},

    {"name": "अमावस्या", "emoji": "🌑", "tithi": 30, "paksha": "K",
     "month": None, "deity": "पितृ",
     "desc": "अमावस्या"},

    {"name": "चतुर्थी", "emoji": "🐘", "tithi": 4, "paksha": "S",
     "month": None, "deity": "गणेश",
     "desc": "विनायक चतुर्थी"},

    {"name": "संकष्टी चतुर्थी", "emoji": "🐘", "tithi": 4, "paksha": "K",
     "month": None, "deity": "गणेश",
     "desc": "संकष्टी चतुर्थी"},

    # ── Major Annual Festivals ────────────────────────────────────────
    {"name": "महाशिवरात्रि", "emoji": "🔱", "tithi": 14, "paksha": "K",
     "month": 12, "deity": "शिव",
     "desc": "फाल्गुन कृष्ण चतुर्दशी"},

    {"name": "होली", "emoji": "🎨", "tithi": 15, "paksha": "S",
     "month": 12, "deity": "कृष्ण",
     "desc": "फाल्गुन पूर्णिमा"},

    {"name": "राम नवमी", "emoji": "🏹", "tithi": 9, "paksha": "S",
     "month": 1, "deity": "राम",
     "desc": "चैत्र शुक्ल नवमी"},

    {"name": "हनुमान जयंती", "emoji": "🙏", "tithi": 15, "paksha": "S",
     "month": 1, "deity": "हनुमान",
     "desc": "चैत्र पूर्णिमा"},

    {"name": "अक्षय तृतीया", "emoji": "🌟", "tithi": 3, "paksha": "S",
     "month": 2, "deity": "विष्णु-लक्ष्मी",
     "desc": "वैशाख शुक्ल तृतीया"},

    {"name": "गंगा दशहरा", "emoji": "🌊", "tithi": 10, "paksha": "S",
     "month": 3, "deity": "गंगा",
     "desc": "ज्येष्ठ शुक्ल दशमी"},

    {"name": "गुरु पूर्णिमा", "emoji": "👨‍🏫", "tithi": 15, "paksha": "S",
     "month": 4, "deity": "गुरु",
     "desc": "आषाढ़ पूर्णिमा"},

    {"name": "नाग पंचमी", "emoji": "🐍", "tithi": 5, "paksha": "S",
     "month": 5, "deity": "नागदेव",
     "desc": "श्रावण शुक्ल पंचमी"},

    {"name": "रक्षाबंधन", "emoji": "🪢", "tithi": 15, "paksha": "S",
     "month": 5, "deity": "यम-यमी",
     "desc": "श्रावण पूर्णिमा"},

    {"name": "जन्माष्टमी", "emoji": "🦚", "tithi": 8, "paksha": "K",
     "month": 5, "deity": "कृष्ण",
     "desc": "भाद्रपद कृष्ण अष्टमी"},

    {"name": "गणेश चतुर्थी", "emoji": "🐘", "tithi": 4, "paksha": "S",
     "month": 6, "deity": "गणेश",
     "desc": "भाद्रपद शुक्ल चतुर्थी"},

    {"name": "नवरात्रि प्रारंभ", "emoji": "🙏", "tithi": 1, "paksha": "S",
     "month": 7, "deity": "दुर्गा",
     "desc": "आश्विन शुक्ल प्रतिपदा"},

    {"name": "दशहरा", "emoji": "🏹", "tithi": 10, "paksha": "S",
     "month": 7, "deity": "राम-दुर्गा",
     "desc": "आश्विन शुक्ल दशमी"},

    {"name": "शरद पूर्णिमा", "emoji": "🌕", "tithi": 15, "paksha": "S",
     "month": 7, "deity": "लक्ष्मी",
     "desc": "आश्विन पूर्णिमा"},

    {"name": "करवा चौथ", "emoji": "💑", "tithi": 4, "paksha": "K",
     "month": 8, "deity": "शिव-पार्वती",
     "desc": "कार्तिक कृष्ण चतुर्थी"},

    {"name": "धनतेरस", "emoji": "💰", "tithi": 13, "paksha": "K",
     "month": 8, "deity": "धन्वंतरि-लक्ष्मी",
     "desc": "कार्तिक कृष्ण त्रयोदशी"},

    {"name": "दीपावली", "emoji": "🪔", "tithi": 15, "paksha": "K",
     "month": 8, "deity": "लक्ष्मी",
     "desc": "कार्तिक अमावस्या"},

    {"name": "गोवर्धन पूजा", "emoji": "🐄", "tithi": 1, "paksha": "S",
     "month": 8, "deity": "कृष्ण",
     "desc": "कार्तिक शुक्ल प्रतिपदा"},

    {"name": "भाई दूज", "emoji": "👫", "tithi": 2, "paksha": "S",
     "month": 8, "deity": "यमराज",
     "desc": "कार्तिक शुक्ल द्वितीया"},

    {"name": "देव उठनी एकादशी", "emoji": "🙏", "tithi": 11, "paksha": "S",
     "month": 8, "deity": "विष्णु",
     "desc": "कार्तिक शुक्ल एकादशी"},
]

# ── Swisseph: Get Today's Tithi & Lunar Month ─────────────────────────
def get_today_panchang():
    """Returns tithi number, paksha (S/K), lunar month (1-12)"""
    try:
        now = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
        jd  = swe.julday(now.year, now.month, now.day,
                         now.hour + now.minute / 60.0)
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        ayan = swe.get_ayanamsa_ut(jd)

        # Sun and Moon longitudes (sidereal)
        sun_lon  = (swe.calc_ut(jd, swe.SUN,  swe.FLG_SWIEPH)[0][0] - ayan) % 360
        moon_lon = (swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH)[0][0] - ayan) % 360

        # Tithi = every 12° difference between moon and sun
        diff  = (moon_lon - sun_lon) % 360
        tithi = int(diff / 12) + 1  # 1-30

        # Paksha
        paksha = "S" if tithi <= 15 else "K"
        tithi_in_paksha = tithi if tithi <= 15 else tithi - 15

        # Lunar month from Sun's sidereal position
        lunar_month = int(sun_lon / 30) + 1  # 1-12

        return {
            "tithi": tithi_in_paksha,
            "tithi_raw": tithi,
            "paksha": paksha,
            "lunar_month": lunar_month,
            "moon_rashi": int(moon_lon / 30),
            "nakshatra": int(moon_lon / (360/27))
        }
    except Exception as e:
        print(f"  ❌ Panchang error: {e}")
        return None


def get_today_festivals(panchang):
    """Match today's panchang against festival rules"""
    if not panchang:
        return []

    festivals = []
    for rule in FESTIVAL_RULES:
        tithi_match  = rule["tithi"] == panchang["tithi"]
        paksha_match = rule["paksha"] == panchang["paksha"]
        month_match  = (rule["month"] is None or
                        rule["month"] == panchang["lunar_month"])

        if tithi_match and paksha_match and month_match:
            festivals.append(rule)

    return festivals


# ── Gemini: Personalized Festival Remedy ─────────────────────────────
def call_gemini(prompt):
    if not GEMINI_API_KEYS:
        return None
    keys = GEMINI_API_KEYS.copy()
    random.shuffle(keys)
    for key in keys[:3]:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{GEMINI_MODEL}:generateContent?key={key}")
        try:
            r = requests.post(
                url,
                json={"contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"temperature": 0.7}},
                timeout=25, verify=False
            )
            if r.status_code == 200:
                text = (r.json().get("candidates", [{}])[0]
                        .get("content", {}).get("parts", [{}])[0]
                        .get("text", "").strip())
                return re.sub(r'[*#]', '', text) if text else None
            elif r.status_code == 429:
                time.sleep(2)
        except Exception:
            time.sleep(1)
    return None


def generate_festival_remedy(user_name, rashi_name, festival, profession, challenge):
    """Generate personalized remedy for festival based on user profile"""
    today = datetime.date.today().strftime("%d %B, %Y")
    prompt = f"""
आज की तारीख: {today}
आज का पर्व/व्रत: {festival['name']} ({festival['desc']})
पर्व देवता: {festival['deity']}

उपयोगकर्ता विवरण:
नाम: {user_name}
राशि: {rashi_name}
पेशा: {profession or 'सामान्य'}
वर्तमान चुनौती: {challenge or 'सामान्य'}

कार्य:
इस {festival['name']} पर {user_name} जी के लिए 3-4 लाइन का व्यक्तिगत संदेश लिखें।
- {festival['deity']} की महिमा एक लाइन में बताएं
- {rashi_name} राशि के अनुसार आज का एक सरल उपाय बताएं
- उनकी चुनौती ({challenge}) के संदर्भ में सकारात्मक मार्गदर्शन दें

नियम:
- केवल हिंदी में
- कोई Markdown नहीं
- '{user_name} जी,' से शुरू करें
- सकारात्मक और प्रेरक भाषा
"""
    return call_gemini(prompt)


# ── Main Festival Notification Function ──────────────────────────────
def send_festival_notifications():
    print("\n" + "─" * 55)
    print("  🎊 Festival Notification Engine")
    print("─" * 55)

    panchang = get_today_panchang()
    if not panchang:
        print("  ❌ Panchang calculation failed")
        return

    print(f"  📅 Tithi: {panchang['tithi']} | "
          f"Paksha: {panchang['paksha']} | "
          f"Month: {LUNAR_MONTHS[panchang['lunar_month']-1]}")

    festivals = get_today_festivals(panchang)
    if not festivals:
        print("  ℹ️  आज कोई विशेष पर्व नहीं है")
        return

    print(f"  🎉 आज के पर्व: {[f['name'] for f in festivals]}")

    # Use primary festival (first match)
    festival = festivals[0]
    print(f"\n  🔔 Sending: {festival['emoji']} {festival['name']}")

    RASHI_NAMES = ["मेष","वृषभ","मिथुन","कर्क","सिंह","कन्या",
                   "तुला","वृश्चिक","धनु","मकर","कुंभ","मीन"]

    profiles = UserProfile.objects.select_related("user").all()
    sent = failed = skipped = 0

    for profile in profiles:
        # Must have active push subscription
        subs = PushSubscription.objects.filter(
            user=profile.user, is_active=True
        )
        if not subs.exists():
            skipped += 1
            continue

        user_name = profile.user.first_name or profile.user.username

        # Get user's moon rashi from profile or use today's moon rashi
        rashi_idx  = getattr(profile, 'moon_rashi_idx', panchang['moon_rashi'])
        rashi_name = RASHI_NAMES[rashi_idx % 12]

        # Generate personalized remedy
        remedy = generate_festival_remedy(
            user_name,
            rashi_name,
            festival,
            getattr(profile, 'profession', ''),
            getattr(profile, 'current_challenge', '')
        )

        if not remedy:
            # Fallback generic message
            remedy = (f"{user_name} जी, आज {festival['name']} के शुभ अवसर पर "
                      f"{festival['deity']} की पूजा करें और उनका आशीर्वाद प्राप्त करें। "
                      f"यह दिन आपके लिए शुभ फल लेकर आएगा। 🙏")

        # Short preview for notification
        preview = remedy[:90] + "..."

        # Send push notification
        send_push_to_user(
            profile.user,
            f"{festival['emoji']} {festival['name']} की शुभकामनाएं!",
            preview,
            "/profile/"  # Opens user's profile/horoscope page
        )

        print(f"    ✅ {user_name} ({rashi_name})")
        sent += 1
        time.sleep(0.3)  # Rate limit

    print(f"\n  📲 Sent: {sent} | ❌ Failed: {failed} | ⏭️ Skipped: {skipped}")
    print("─" * 55)


if __name__ == "__main__":
    send_festival_notifications()