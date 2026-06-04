import os, sys, datetime, requests, random, re, time
import swisseph as swe
import pytz
from pathlib import Path

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
# यह चेक करेगा कि Django पहले से लोड तो नहीं है (ताकि views में import करते वक्त एरर न आए)
if not django.apps.apps.ready: 
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

# ── Lunar Month Names (Amanta System) ────────────────────────────────
LUNAR_MONTHS = [
    "चैत्र", "वैशाख", "ज्येष्ठ", "आषाढ़", "श्रावण", "भाद्रपद",
    "आश्विन", "कार्तिक", "मार्गशीर्ष", "पौष", "माघ", "फाल्गुन"
]

RASHI_NAMES = [
    "मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या",
    "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"
]

# ── Festival Rules ────────────────────────────────────────────────────
FESTIVAL_RULES = [
    {"name": "एकादशी",          "emoji": "🙏",  "tithi": 11, "paksha": "S", "month": None, "deity": "विष्णु",       "desc": "शुक्ल एकादशी व्रत"},
    {"name": "एकादशी",          "emoji": "🙏",  "tithi": 11, "paksha": "K", "month": None, "deity": "विष्णु",       "desc": "कृष्ण एकादशी व्रत"},
    {"name": "प्रदोष व्रत",     "emoji": "🕉️", "tithi": 13, "paksha": "S", "month": None, "deity": "शिव",          "desc": "शुक्ल प्रदोष"},
    {"name": "प्रदोष व्रत",     "emoji": "🕉️", "tithi": 13, "paksha": "K", "month": None, "deity": "शिव",          "desc": "कृष्ण प्रदोष"},
    {"name": "पूर्णिमा",        "emoji": "🌕",  "tithi": 15, "paksha": "S", "month": None, "deity": "चंद्र",        "desc": "पूर्णिमा तिथि"},
    {"name": "अमावस्या",        "emoji": "🌑",  "tithi": 15, "paksha": "K", "month": None, "deity": "पितृ",          "desc": "अमावस्या तिथि"},
    {"name": "विनायक चतुर्थी",  "emoji": "🐘",  "tithi": 4,  "paksha": "S", "month": None, "deity": "गणेश",          "desc": "विनायक चतुर्थी"},
    {"name": "संकष्टी चतुर्थी", "emoji": "🐘",  "tithi": 4,  "paksha": "K", "month": None, "deity": "गणेश",          "desc": "संकष्टी चतुर्थी"},
    
    # ── Major Annual Festivals ──
    {"name": "महाशिवरात्रि",    "emoji": "🔱",  "tithi": 14, "paksha": "K", "month": 12,   "deity": "शिव",           "desc": "फाल्गुन कृष्ण चतुर्दशी"},
    {"name": "होली",            "emoji": "🎨",  "tithi": 15, "paksha": "S", "month": 12,   "deity": "कृष्ण",         "desc": "फाल्गुन पूर्णिमा"},
    {"name": "राम नवमी",        "emoji": "🏹",  "tithi": 9,  "paksha": "S", "month": 1,    "deity": "राम",            "desc": "चैत्र शुक्ल नवमी"},
    {"name": "हनुमान जयंती",    "emoji": "🙏",  "tithi": 15, "paksha": "S", "month": 1,    "deity": "हनुमान",         "desc": "चैत्र पूर्णिमा"},
    {"name": "अक्षय तृतीया",    "emoji": "🌟",  "tithi": 3,  "paksha": "S", "month": 2,    "deity": "विष्णु-लक्ष्मी", "desc": "वैशाख शुक्ल तृतीया"},
    {"name": "गंगा दशहरा",      "emoji": "🌊",  "tithi": 10, "paksha": "S", "month": 3,    "deity": "गंगा",           "desc": "ज्येष्ठ शुक्ल दशमी"},
    {"name": "गुरु पूर्णिमा",   "emoji": "👨‍🏫", "tithi": 15, "paksha": "S", "month": 4,    "deity": "गुरु",           "desc": "आषाढ़ पूर्णिमा"},
    {"name": "नाग पंचमी",       "emoji": "🐍",  "tithi": 5,  "paksha": "S", "month": 5,    "deity": "नागदेव",         "desc": "श्रावण शुक्ल पंचमी"},
    {"name": "रक्षाबंधन",       "emoji": "🪢",  "tithi": 15, "paksha": "S", "month": 5,    "deity": "यम-यमी",         "desc": "श्रावण पूर्णिमा"},
    {"name": "जन्माष्टमी",      "emoji": "🦚",  "tithi": 8,  "paksha": "K", "month": 5,    "deity": "कृष्ण",          "desc": "भाद्रपद कृष्ण अष्टमी"},
    {"name": "गणेश चतुर्थी",    "emoji": "🐘",  "tithi": 4,  "paksha": "S", "month": 6,    "deity": "गणेश",           "desc": "भाद्रपद शुक्ल चतुर्थी"},
    {"name": "नवरात्रि प्रारंभ","emoji": "🙏",  "tithi": 1,  "paksha": "S", "month": 7,    "deity": "दुर्गा",         "desc": "आश्विन शुक्ल प्रतिपदा"},
    {"name": "दशहरा",           "emoji": "🏹",  "tithi": 10, "paksha": "S", "month": 7,    "deity": "राम-दुर्गा",     "desc": "आश्विन शुक्ल दशमी"},
    {"name": "शरद पूर्णिमा",    "emoji": "🌕",  "tithi": 15, "paksha": "S", "month": 7,    "deity": "लक्ष्मी",        "desc": "आश्विन पूर्णिमा"},
    {"name": "करवा चौथ",        "emoji": "💑",  "tithi": 4,  "paksha": "K", "month": 8,    "deity": "शिव-पार्वती",    "desc": "कार्तिक कृष्ण चतुर्थी"},
    {"name": "धनतेरस",          "emoji": "💰",  "tithi": 13, "paksha": "K", "month": 8,    "deity": "धन्वंतरि-लक्ष्मी","desc": "कार्तिक कृष्ण त्रयोदशी"},
    {"name": "दीपावली",         "emoji": "🪔",  "tithi": 15, "paksha": "K", "month": 8,    "deity": "लक्ष्मी",        "desc": "कार्तिक अमावस्या"},
    {"name": "गोवर्धन पूजा",    "emoji": "🐄",  "tithi": 1,  "paksha": "S", "month": 8,    "deity": "कृष्ण",          "desc": "कार्तिक शुक्ल प्रतिपदा"},
    {"name": "भाई दूज",         "emoji": "👫",  "tithi": 2,  "paksha": "S", "month": 8,    "deity": "यमराज",          "desc": "कार्तिक शुक्ल द्वितीया"},
    {"name": "देव उठनी एकादशी", "emoji": "🙏",  "tithi": 11, "paksha": "S", "month": 8,    "deity": "विष्णु",         "desc": "कार्तिक शुक्ल एकादशी"},
]

# ── Panchang Calculation ──────────────────────────────────────────
def get_today_panchang():
    try:
        from datetime import timedelta
        now    = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
        dt_utc = now - timedelta(hours=5, minutes=30)
        jd_ut  = swe.julday(
            dt_utc.year, dt_utc.month, dt_utc.day,
            dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
        )
        swe.set_sid_mode(swe.SIDM_LAHIRI)

        res_sun,  _ = swe.calc_ut(jd_ut, swe.SUN,  swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
        res_moon, _ = swe.calc_ut(jd_ut, swe.MOON, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
        sun_lon  = res_sun[0]
        moon_lon = res_moon[0]

        tithi_idx = int(((moon_lon - sun_lon) % 360) / 12.0)
        paksha    = "S" if tithi_idx < 15 else "K"
        tithi_num = (tithi_idx % 15) + 1                       

        moon_sun_diff       = (moon_lon - sun_lon) % 360
        days_since_amavasya = moon_sun_diff / 12.190749
        amavasya_sun_lon    = (sun_lon - (days_since_amavasya * 0.9856)) % 360
        lunar_month_idx     = int(amavasya_sun_lon / 30)       

        tithi_names = [
            "प्रतिपदा", "द्वितीया",  "तृतीया",    "चतुर्थी",   "पंचमी",
            "षष्ठी",    "सप्तमी",    "अष्टमी",    "नवमी",      "दशमी",
            "एकादशी",   "द्वादशी",   "त्रयोदशी",  "चतुर्दशी",  "पूर्णिमा",
            "प्रतिपदा", "द्वितीया",  "तृतीया",    "चतुर्थी",   "पंचमी",
            "षष्ठी",    "सप्तमी",    "अष्टमी",    "नवमी",      "दशमी",
            "एकादशी",   "द्वादशी",   "त्रयोदशी",  "चतुर्दशी",  "अमावस्या"
        ]

        return {
            "tithi":       tithi_num,
            "tithi_idx":   tithi_idx,
            "tithi_name":  tithi_names[tithi_idx],
            "paksha":      paksha,
            "lunar_month": lunar_month_idx,   
            "moon_rashi":  int(moon_lon / 30),
            "nakshatra":   int(moon_lon / (360 / 27.0)),
        }

    except Exception as e:
        print(f"❌ Panchang error: {e}")
        return None

# ── Festival Matching (यह फंक्शन Views के लिए ज़रूरी है) ─────────
# ── Festival Matching (Updated to handle both formats) ─────────
def get_today_festivals(panchang_data=None):
    panchang = panchang_data if panchang_data else get_today_panchang()
    if not panchang: return []

    # हिंदी तिथि को नंबर में बदलने का मैप
    tithi_map = {
        "प्रतिपदा": 1, "द्वितीया": 2, "तृतीया": 3, "चतुर्थी": 4, "पंचमी": 5,
        "षष्ठी": 6, "सप्तमी": 7, "अष्टमी": 8, "नवमी": 9, "दशमी": 10,
        "एकादशी": 11, "द्वादशी": 12, "त्रयोदशी": 13, "चतुर्दशी": 14, 
        "पूर्णिमा": 15, "अमावस्या": 15
    }

    # 1. Tithi (तिथि) मैच करें
    p_tithi = panchang.get('tithi', 1)
    if isinstance(p_tithi, str):
        clean_tithi = p_tithi.split()[0] if ' ' in p_tithi else p_tithi
        p_tithi = tithi_map.get(clean_tithi, 1)

    # 2. Paksha (पक्ष) मैच करें
    p_paksha = panchang.get('paksha', 'S')
    if isinstance(p_paksha, str):
        if "शुक्ल" in p_paksha: p_paksha = "S"
        elif "कृष्ण" in p_paksha: p_paksha = "K"

    # 3. Month (महीना) मैच करें (वेबसाइट से hindu_maas के नाम से आता है)
    p_month = panchang.get('lunar_month')
    if not p_month and 'hindu_maas' in panchang:
        p_month = panchang['hindu_maas']
        
    if isinstance(p_month, str):
        # अगर अधिक मास है तो उसे क्लीन करें
        clean_month = p_month.replace('अधिक', '').replace('क्षय', '').strip()
        try:
            p_month_idx = LUNAR_MONTHS.index(clean_month) + 1
        except ValueError:
            p_month_idx = 1
    else:
        p_month_idx = (p_month or 0) + 1

    festivals = []
    for rule in FESTIVAL_RULES:
        if rule["tithi"] == p_tithi and rule["paksha"] == p_paksha:
            if rule["month"] is None or rule["month"] == p_month_idx:
                festivals.append(rule)

    return festivals

# ── Main Background Task ─────────────────────────────────────────────
def send_festival_notifications():
    print("\n" + "─" * 55)
    print("  🎊 Festival Notification Engine")
    print("─" * 55)

    panchang = get_today_panchang()
    if not panchang: return

    festivals = get_today_festivals(panchang)
    if not festivals:
        print("  ℹ️  आज कोई विशेष पर्व नहीं है")
        return

    festival = festivals[0]
    print(f"  🔔 Sending Push for: {festival['emoji']} {festival['name']}")

    profiles = UserProfile.objects.select_related("user").all()
    sent = 0

    for profile in profiles:
        subs = PushSubscription.objects.filter(user=profile.user, is_active=True)
        if not subs.exists(): continue

        user_name  = profile.user.first_name or profile.user.username
        
        remedy = f"{user_name} जी, आज {festival['name']} के शुभ अवसर पर {festival['deity']} की पूजा करें और उनका आशीर्वाद प्राप्त करें। यह दिन आपके लिए शुभ फल लेकर आएगा। 🙏"
        preview = remedy[:90] + "..."

        send_push_to_user(
            profile.user,
            f"{festival['emoji']} {festival['name']} की शुभकामनाएं!",
            preview,
            "/?tab=view-panchang"
        )
        sent += 1

    print(f"  📲 Sent: {sent}")
    print("─" * 55)

if __name__ == "__main__":
    send_festival_notifications()
