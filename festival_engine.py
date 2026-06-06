import os, sys, datetime, re
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
if not django.apps.apps.ready: 
    django.setup()

from core.models import UserProfile, PushSubscription, SavedKundali, UserNotification
from core.views.push_views import send_push_to_user

import random
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Gemini Setup
GEMINI_API_KEYS = []
for _i in range(1, 10):
    _k = os.environ.get(f"GEMINI_API_KEYS{_i}", "").strip()
    if _k: GEMINI_API_KEYS.append(_k)
GEMINI_MODEL = "gemini-2.0-flash-exp"

def _call_gemini_festival(prompt):
    if not GEMINI_API_KEYS: return ""
    keys = GEMINI_API_KEYS.copy()
    random.shuffle(keys)
    for api_key in keys[:3]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}"
        try:
            resp = requests.post(url, json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.8, "maxOutputTokens": 300}
            }, timeout=25, verify=False)
            if resp.status_code == 200:
                text = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                import re
                return re.sub(r'[*#]', '', text) if text else ""
            elif resp.status_code == 429:
                import time; time.sleep(2)
        except Exception:
            import time; time.sleep(1)
    return ""

def build_festival_remedy_prompt(user_name, profile, festival, natal_pos, lagna_idx, dasha):
    import datetime
    today_str = datetime.date.today().strftime("%d %B %Y")
    RASHI_NAMES = ["मेष","वृषभ","मिथुन","कर्क","सिंह","कन्या","तुला","वृश्चिक","धनु","मकर","कुंभ","मीन"]
    chandra_rashi = natal_pos.get("चंद्र", {}).get("rashi", "अज्ञात")
    chandra_nak   = natal_pos.get("चंद्र", {}).get("nakshatra", "")
    lagna_name    = RASHI_NAMES[lagna_idx] if 0 <= lagna_idx < 12 else "अज्ञात"
    guru   = natal_pos.get("गुरु",  {}).get("rashi", "")
    shukra = natal_pos.get("शुक्र", {}).get("rashi", "")
    shani  = natal_pos.get("शनि",  {}).get("rashi", "")
    festival_name  = festival.get("name", "")
    festival_deity = festival.get("deity", "भगवान")
    festival_desc  = festival.get("desc", "")
    community      = festival.get("community", "Hindu")
    lines = [
        f"आज की तारीख: {today_str}",
        "आप एक श्रेष्ठ वैदिक ज्योतिषी और धर्मशास्त्री हैं।",
        "",
        f"आज का पर्व: {festival_name} ({festival_desc})",
        f"देवता: {festival_deity} | समुदाय: {community}",
        "",
        "उपयोगकर्ता की जन्म-कुंडली:",
        f"  नाम: {user_name}",
        f"  जन्म लग्न: {lagna_name}",
        f"  चंद्र राशि: {chandra_rashi} ({chandra_nak})",
        f"  महादशा: {dasha.get('md','अज्ञात')} | अंतर्दशा: {dasha.get('ad','अज्ञात')}",
        f"  पेशा: {profile.profession or 'सामान्य'}",
        f"  जीवन फोकस: {profile.primary_focus or 'सामान्य'}",
        f"  गुरु: {guru} | शुक्र: {shukra} | शनि: {shani}",
        "",
        "नियम:",
        "1. सिर्फ 3-4 पंक्तियाँ — छोटा, सटीक और व्यक्तिगत।",
        f"2. '{user_name} जी,' से शुरू करें।",
        "3. इस पर्व पर उनकी कुंडली के अनुसार कौन सा विशेष उपाय/पूजा सबसे लाभकारी होगा — स्पष्ट बताएं।",
        "4. उपाय व्यावहारिक हो — घर पर आसानी से हो सके।",
        "5. अंत में एक छोटा मंत्र दें जो इस पर्व और देवता से संबंधित हो।",
    ]
    return "\n".join(lines)


# ── Lunar Month Names (Amanta System) ────────────────────────────────
LUNAR_MONTHS = [
    "चैत्र", "वैशाख", "ज्येष्ठ", "आषाढ़", "श्रावण", "भाद्रपद",
    "आश्विन", "कार्तिक", "मार्गशीर्ष", "पौष", "माघ", "फाल्गुन"
]

# ── Festival Rules (Master List + Time-Shift Logic) ──────────────────
# time_slot: "afternoon" (2 PM), "evening" (7 PM), "midnight" (11:30 PM), "predawn" (4 AM)
FESTIVAL_RULES = [
    # ── सामान्य मासिक व्रत ──
    {"name": "एकादशी",          "emoji": "🙏",  "tithi": 11, "paksha": "S", "month": None, "deity": "विष्णु",       "desc": "शुक्ल एकादशी व्रत"},
    {"name": "एकादशी",          "emoji": "🙏",  "tithi": 11, "paksha": "K", "month": None, "deity": "विष्णु",       "desc": "कृष्ण एकादशी व्रत"},
    {"name": "प्रदोष व्रत",     "emoji": "🕉️", "tithi": 13, "paksha": "S", "month": None, "deity": "शिव",          "desc": "शुक्ल प्रदोष", "time_slot": "evening"},
    {"name": "प्रदोष व्रत",     "emoji": "🕉️", "tithi": 13, "paksha": "K", "month": None, "deity": "शिव",          "desc": "कृष्ण प्रदोष", "time_slot": "evening"},
    {"name": "पूर्णिमा",        "emoji": "🌕",  "tithi": 15, "paksha": "S", "month": None, "deity": "चंद्र",        "desc": "पूर्णिमा तिथि"},
    {"name": "अमावस्या",        "emoji": "🌑",  "tithi": 15, "paksha": "K", "month": None, "deity": "पितृ",          "desc": "अमावस्या तिथि"},
    {"name": "संकष्टी चतुर्थी", "emoji": "🐘",  "tithi": 4,  "paksha": "K", "month": None, "deity": "गणेश",          "desc": "संकष्टी चतुर्थी", "time_slot": "evening"},
    
    # ── चैत्र (1) ──
    {"name": "चैत्र नवरात्रि / नववर्ष", "emoji": "🚩", "tithi": 1,  "paksha": "S", "month": 1, "deity": "दुर्गा/ब्रह्मा", "desc": "चैत्र शुक्ल प्रतिपदा"},
    {"name": "गणगौर पूजा",            "emoji": "🌸", "tithi": 3,  "paksha": "S", "month": 1, "deity": "शिव-पार्वती", "desc": "चैत्र शुक्ल तृतीया"},
    {"name": "यमुना छठ",              "emoji": "🌊", "tithi": 6,  "paksha": "S", "month": 1, "deity": "यमुना", "desc": "चैत्र शुक्ल षष्ठी"},
    {"name": "राम नवमी",              "emoji": "🏹", "tithi": 9,  "paksha": "S", "month": 1, "deity": "राम", "desc": "चैत्र शुक्ल नवमी", "time_slot": "afternoon"},
    {"name": "कामदा एकादशी",          "emoji": "🙏", "tithi": 11, "paksha": "S", "month": 1, "deity": "विष्णु", "desc": "चैत्र शुक्ल एकादशी"},
    {"name": "हनुमान जयंती",          "emoji": "🐒", "tithi": 15, "paksha": "S", "month": 1, "deity": "हनुमान", "desc": "चैत्र पूर्णिमा"},
    {"name": "वरूथिनी एकादशी",        "emoji": "🙏", "tithi": 11, "paksha": "K", "month": 1, "deity": "विष्णु", "desc": "चैत्र कृष्ण एकादशी"},

    # ── वैशाख (2) ──
    {"name": "अक्षय तृतीया",          "emoji": "🌟", "tithi": 3,  "paksha": "S", "month": 2, "deity": "विष्णु-लक्ष्मी", "desc": "वैशाख शुक्ल तृतीया"},
    {"name": "सीता नवमी",             "emoji": "👑", "tithi": 9,  "paksha": "S", "month": 2, "deity": "सीता", "desc": "वैशाख शुक्ल नवमी"},
    {"name": "मोहिनी एकादशी",         "emoji": "🙏", "tithi": 11, "paksha": "S", "month": 2, "deity": "विष्णु", "desc": "वैशाख शुक्ल एकादशी"},
    {"name": "नरसिंह जयंती",           "emoji": "🦁", "tithi": 14, "paksha": "S", "month": 2, "deity": "नरसिंह", "desc": "वैशाख शुक्ल चतुर्दशी", "time_slot": "evening"},
    {"name": "कूर्म जयंती / पूर्णिमा",  "emoji": "🐢", "tithi": 15, "paksha": "S", "month": 2, "deity": "विष्णु", "desc": "वैशाख पूर्णिमा"},
    {"name": "परशुराम जयंती",            "emoji": "🪓", "tithi": 3,  "paksha": "S", "month": 2, "deity": "परशुराम",      "desc": "वैशाख शुक्ल तृतीया (अक्षय तृतीया के दिन)"},
    {"name": "अपरा एकादशी",           "emoji": "🙏", "tithi": 11, "paksha": "K", "month": 2, "deity": "विष्णु", "desc": "वैशाख कृष्ण एकादशी"},
    {"name": "शनि जयंती / वट सावित्री", "emoji": "🪐", "tithi": 15, "paksha": "K", "month": 2, "deity": "शनिदेव", "desc": "वैशाख अमावस्या (अमांत)"},

    # ── ज्येष्ठ (3) ──
    {"name": "गंगा दशहरा",            "emoji": "🌊", "tithi": 10, "paksha": "S", "month": 3, "deity": "गंगा", "desc": "ज्येष्ठ शुक्ल दशमी"},
    {"name": "निर्जला एकादशी",        "emoji": "💧", "tithi": 11, "paksha": "S", "month": 3, "deity": "विष्णु", "desc": "ज्येष्ठ शुक्ल एकादशी"},
    {"name": "वट पूर्णिमा व्रत",          "emoji": "🌳", "tithi": 15, "paksha": "S", "month": 3, "deity": "सावित्री", "desc": "ज्येष्ठ पूर्णिमा"},
    {"name": "योगिनी एकादशी",         "emoji": "🙏", "tithi": 11, "paksha": "K", "month": 3, "deity": "विष्णु", "desc": "ज्येष्ठ कृष्ण एकादशी"},

    # ── आषाढ़ (4) ──
    {"name": "देवशयनी एकादशी",        "emoji": "🛌", "tithi": 11, "paksha": "S", "month": 4, "deity": "विष्णु", "desc": "आषाढ़ शुक्ल एकादशी"},
    {"name": "गुरु पूर्णिमा (व्यास पूजा)", "emoji": "👨‍🏫", "tithi": 15, "paksha": "S", "month": 4, "deity": "गुरु", "desc": "आषाढ़ पूर्णिमा"},
    {"name": "कामिका एकादशी",         "emoji": "🙏", "tithi": 11, "paksha": "K", "month": 4, "deity": "विष्णु", "desc": "आषाढ़ कृष्ण एकादशी"},

    # ── श्रावण (5) ──
    {"name": "हरियाली तीज",           "emoji": "🌿", "tithi": 3,  "paksha": "S", "month": 5, "deity": "शिव-पार्वती", "desc": "श्रावण शुक्ल तृतीया"},
    {"name": "नाग पंचमी",             "emoji": "🐍", "tithi": 5,  "paksha": "S", "month": 5, "deity": "नागदेव", "desc": "श्रावण शुक्ल पंचमी"},
    {"name": "श्रावण पुत्रदा एकादशी",   "emoji": "🙏", "tithi": 11, "paksha": "S", "month": 5, "deity": "विष्णु", "desc": "श्रावण शुक्ल एकादशी"},
    {"name": "रक्षाबंधन",             "emoji": "🪢", "tithi": 15, "paksha": "S", "month": 5, "deity": "यम-यमी", "desc": "श्रावण पूर्णिमा"},
    {"name": "कजरी तीज",             "emoji": "🍃", "tithi": 3,  "paksha": "K", "month": 5, "deity": "पार्वती", "desc": "श्रावण कृष्ण तृतीया"},
    {"name": "श्री कृष्ण जन्माष्टमी",     "emoji": "🦚", "tithi": 8,  "paksha": "K", "month": 5, "deity": "कृष्ण", "desc": "श्रावण कृष्ण अष्टमी (अमांत)", "time_slot": "midnight"},
    {"name": "अजा एकादशी",            "emoji": "🙏", "tithi": 11, "paksha": "K", "month": 5, "deity": "विष्णु", "desc": "श्रावण कृष्ण एकादशी"},

    # ── भाद्रपद (6) ──
    {"name": "हरितालिका तीज",         "emoji": "👸", "tithi": 3,  "paksha": "S", "month": 6, "deity": "शिव-पार्वती", "desc": "भाद्रपद शुक्ल तृतीया"},
    {"name": "गणेश चतुर्थी",           "emoji": "🐘", "tithi": 4,  "paksha": "S", "month": 6, "deity": "गणेश", "desc": "भाद्रपद शुक्ल चतुर्थी", "time_slot": "afternoon"},
    {"name": "ऋषि पंचमी",             "emoji": "🧘", "tithi": 5,  "paksha": "S", "month": 6, "deity": "सप्तर्षि", "desc": "भाद्रपद शुक्ल पंचमी"},
    {"name": "राधा अष्टमी",            "emoji": "🌸", "tithi": 8,  "paksha": "S", "month": 6, "deity": "राधा", "desc": "भाद्रपद शुक्ल अष्टमी"},
    {"name": "पार्श्व (वामन) एकादशी",   "emoji": "🙏", "tithi": 11, "paksha": "S", "month": 6, "deity": "विष्णु/वामन", "desc": "भाद्रपद शुक्ल एकादशी"},
    {"name": "अनंत चतुर्दशी",          "emoji": "♾️", "tithi": 14, "paksha": "S", "month": 6, "deity": "विष्णु", "desc": "भाद्रपद शुक्ल चतुर्दशी"},
    {"name": "इन्दिरा एकादशी",         "emoji": "🙏", "tithi": 11, "paksha": "K", "month": 6, "deity": "विष्णु", "desc": "भाद्रपद कृष्ण एकादशी"},
    {"name": "सर्वपित्री अमावस्या",       "emoji": "🌑", "tithi": 15, "paksha": "K", "month": 6, "deity": "पितृ", "desc": "भाद्रपद अमावस्या (महालया)"},

    # ── आश्विन/आसो (7) ──
    {"name": "शारदीय नवरात्रि प्रारंभ",   "emoji": "🚩", "tithi": 1,  "paksha": "S", "month": 7, "deity": "शैलपुत्री", "desc": "आश्विन शुक्ल प्रतिपदा"},
    {"name": "दुर्गा अष्टमी (महाअष्टमी)",  "emoji": "🔱", "tithi": 8,  "paksha": "S", "month": 7, "deity": "महागौरी", "desc": "आश्विन शुक्ल अष्टमी"},
    {"name": "महानवमी",              "emoji": "🔥", "tithi": 9,  "paksha": "S", "month": 7, "deity": "सिद्धिदात्री", "desc": "आश्विन शुक्ल नवमी"},
    {"name": "विजयादशमी (दशहरा)",     "emoji": "🏹", "tithi": 10, "paksha": "S", "month": 7, "deity": "राम-दुर्गा", "desc": "आश्विन शुक्ल दशमी", "time_slot": "afternoon"},
    {"name": "पापांकुशा एकादशी",       "emoji": "🙏", "tithi": 11, "paksha": "S", "month": 7, "deity": "विष्णु", "desc": "आश्विन शुक्ल एकादशी"},
    {"name": "शरद पूर्णिमा (कोजागिरी)", "emoji": "🌕", "tithi": 15, "paksha": "S", "month": 7, "deity": "लक्ष्मी", "desc": "आश्विन पूर्णिमा", "time_slot": "evening"},
    {"name": "करवा चौथ",             "emoji": "💑", "tithi": 4,  "paksha": "K", "month": 7, "deity": "शिव-पार्वती", "desc": "आश्विन कृष्ण चतुर्थी", "time_slot": "evening"},
    {"name": "अहोई अष्टमी",           "emoji": "👩‍👧‍👦", "tithi": 8, "paksha": "K", "month": 7, "deity": "अहोई माता", "desc": "आश्विन कृष्ण अष्टमी"},
    {"name": "रमा एकादशी",            "emoji": "🙏", "tithi": 11, "paksha": "K", "month": 7, "deity": "विष्णु", "desc": "आश्विन कृष्ण एकादशी"},
    {"name": "धनतेरस",               "emoji": "💰", "tithi": 13, "paksha": "K", "month": 7, "deity": "धन्वंतरि-लक्ष्मी", "desc": "आश्विन कृष्ण त्रयोदशी", "time_slot": "evening"},
    {"name": "नरक चतुर्दशी (रूप चौदस)","emoji": "🪔", "tithi": 14, "paksha": "K", "month": 7, "deity": "कृष्ण-काली", "desc": "आश्विन कृष्ण चतुर्दशी", "time_slot": "predawn"},
    {"name": "दीपावली",              "emoji": "🪔", "tithi": 15, "paksha": "K", "month": 7, "deity": "लक्ष्मी", "desc": "आश्विन अमावस्या", "time_slot": "evening"},

    # ── कार्तिक (8) ──
    {"name": "गोवर्धन पूजा",           "emoji": "🐄", "tithi": 1,  "paksha": "S", "month": 8, "deity": "कृष्ण", "desc": "कार्तिक शुक्ल प्रतिपदा"},
    {"name": "भाई दूज (यम द्वितीया)",  "emoji": "👫", "tithi": 2,  "paksha": "S", "month": 8, "deity": "यम-यमुना", "desc": "कार्तिक शुक्ल द्वितीया"},
    {"name": "लाभ पंचमी",            "emoji": "📈", "tithi": 5,  "paksha": "S", "month": 8, "deity": "लक्ष्मी-गणेश", "desc": "कार्तिक शुक्ल पंचमी"},
    {"name": "छठ पूजा",              "emoji": "🌅", "tithi": 6,  "paksha": "S", "month": 8, "deity": "सूर्य-छठी मैया", "desc": "कार्तिक शुक्ल षष्ठी", "time_slot": "evening"},
    {"name": "गोपाष्टमी",             "emoji": "🐮", "tithi": 8,  "paksha": "S", "month": 8, "deity": "गौमाता-कृष्ण", "desc": "कार्तिक शुक्ल अष्टमी"},
    {"name": "आंवला (अक्षय) नवमी",     "emoji": "🌳", "tithi": 9,  "paksha": "S", "month": 8, "deity": "विष्णु-आंवला", "desc": "कार्तिक शुक्ल नवमी"},
    {"name": "देव उठनी एकादशी",       "emoji": "🙏", "tithi": 11, "paksha": "S", "month": 8, "deity": "विष्णु", "desc": "कार्तिक शुक्ल एकादशी"},
    {"name": "तुलसी विवाह",           "emoji": "🪴", "tithi": 12, "paksha": "S", "month": 8, "deity": "विष्णु-तुलसी", "desc": "कार्तिक शुक्ल द्वादशी"},
    {"name": "वैकुंठ चतुर्दशी",         "emoji": "🕉️", "tithi": 14, "paksha": "S", "month": 8, "deity": "शिव-विष्णु", "desc": "कार्तिक शुक्ल चतुर्दशी", "time_slot": "midnight"},
    {"name": "कार्तिक पूर्णिमा (देव दिवाली)","emoji": "🪔", "tithi": 15, "paksha": "S", "month": 8, "deity": "शिव (त्रिपुरारी)", "desc": "कार्तिक पूर्णिमा"},
    {"name": "उत्पन्ना एकादशी",       "emoji": "🙏", "tithi": 11, "paksha": "K", "month": 8, "deity": "विष्णु", "desc": "कार्तिक कृष्ण एकादशी"},

    # ── मार्गशीर्ष (9) ──
    {"name": "विवाह पंचमी",           "emoji": "💒", "tithi": 5,  "paksha": "S", "month": 9, "deity": "राम-सीता", "desc": "मार्गशीर्ष शुक्ल पंचमी"},
    {"name": "गीता जयंती / मोक्षदा",   "emoji": "📖", "tithi": 11, "paksha": "S", "month": 9, "deity": "कृष्ण/विष्णु", "desc": "मार्गशीर्ष शुक्ल एकादशी"},
    {"name": "दत्तात्रेय जयंती",         "emoji": "🕉️", "tithi": 15, "paksha": "S", "month": 9, "deity": "दत्तात्रेय", "desc": "मार्गशीर्ष पूर्णिमा"},
    {"name": "सफला एकादशी",           "emoji": "🙏", "tithi": 11, "paksha": "K", "month": 9, "deity": "विष्णु", "desc": "मार्गशीर्ष कृष्ण एकादशी"},

    # ── पौष (10) ──
    {"name": "पौष पुत्रदा एकादशी",     "emoji": "🙏", "tithi": 11, "paksha": "S", "month": 10,"deity": "विष्णु", "desc": "पौष शुक्ल एकादशी"},
    {"name": "शाकंभरी पूर्णिमा",        "emoji": "🌿", "tithi": 15, "paksha": "S", "month": 10,"deity": "शाकंभरी माता", "desc": "पौष पूर्णिमा"},
    {"name": "षटतिला एकादशी",         "emoji": "🙏", "tithi": 11, "paksha": "K", "month": 10,"deity": "विष्णु", "desc": "पौष कृष्ण एकादशी"},
    {"name": "मौनी अमावस्या",         "emoji": "🤫", "tithi": 15, "paksha": "K", "month": 10,"deity": "विष्णु/शिव", "desc": "पौष अमावस्या"},

    # ── माघ (11) ──
    {"name": "माघ गुप्त नवरात्रि प्रारंभ", "emoji": "🚩", "tithi": 1,  "paksha": "S", "month": 11,"deity": "दुर्गा", "desc": "माघ शुक्ल प्रतिपदा"},
    {"name": "वसंत पंचमी",            "emoji": "🌼", "tithi": 5,  "paksha": "S", "month": 11,"deity": "सरस्वती", "desc": "माघ शुक्ल पंचमी"},
    {"name": "रथ (अचला) सप्तमी",      "emoji": "🌞", "tithi": 7,  "paksha": "S", "month": 11,"deity": "सूर्यदेव", "desc": "माघ शुक्ल सप्तमी"},
    {"name": "भीष्म अष्टमी",            "emoji": "🏹", "tithi": 8,  "paksha": "S", "month": 11,"deity": "भीष्म पितामह", "desc": "माघ शुक्ल अष्टमी"},
    {"name": "जया एकादशी",            "emoji": "🙏", "tithi": 11, "paksha": "S", "month": 11,"deity": "विष्णु", "desc": "माघ शुक्ल एकादशी"},
    {"name": "माघ पूर्णिमा (रविदास जयंती)","emoji": "🌕", "tithi": 15, "paksha": "S", "month": 11,"deity": "विष्णु/रविदास", "desc": "माघ पूर्णिमा"},
    {"name": "विजया एकादशी",          "emoji": "🙏", "tithi": 11, "paksha": "K", "month": 11,"deity": "विष्णु", "desc": "माघ कृष्ण एकादशी"},
    {"name": "महाशिवरात्रि",          "emoji": "🔱", "tithi": 14, "paksha": "K", "month": 11,"deity": "शिव", "desc": "माघ कृष्ण चतुर्दशी", "time_slot": "midnight"},

    # ── फाल्गुन (12) ──
    {"name": "आमलकी एकादशी",          "emoji": "🌳", "tithi": 11, "paksha": "S", "month": 12,"deity": "विष्णु-आंवला", "desc": "फाल्गुन शुक्ल एकादशी"},
    {"name": "होलिका दहन",            "emoji": "🔥", "tithi": 15, "paksha": "S", "month": 12,"deity": "विष्णु-प्रहलाद", "desc": "फाल्गुन पूर्णिमा", "time_slot": "evening"},
    {"name": "पापमोचनी एकादशी",       "emoji": "🙏", "tithi": 11, "paksha": "K", "month": 12,"deity": "विष्णु", "desc": "फाल्गुन कृष्ण एकादशी"},
]

# ── Dynamic Tithi Calculator ─────────────────────────────────────────


# ── सौर / Fixed-Date त्यौहार (date aur month se match hote hain) ──
# Format: {"name", "emoji", "day": DD, "month": MM (Gregorian), "deity", "community", "desc"}
SOLAR_FESTIVALS = [
    # ── मकर संक्रांति / उत्तरायण ──
    {"name": "मकर संक्रांति / उत्तरायण", "emoji": "🪁", "day": 14, "month": 1,  "deity": "सूर्यदेव",     "community": "Hindu",    "desc": "सूर्य का मकर राशि में प्रवेश"},
    {"name": "पोंगल",                   "emoji": "🍚", "day": 14, "month": 1,  "deity": "सूर्यदेव",     "community": "Regional", "desc": "तमिलनाडु का फसल उत्सव"},
    {"name": "लोहड़ी",                   "emoji": "🔥", "day": 13, "month": 1,  "deity": "अग्नि",        "community": "Sikh",     "desc": "पंजाब का शीत उत्सव"},
    {"name": "भोगाली बिहू",              "emoji": "🌾", "day": 14, "month": 1,  "deity": "प्रकृति",      "community": "Regional", "desc": "असम का फसल उत्सव (माघ बिहू)"},
    
    # ── गणतंत्र दिवस ──
    {"name": "गणतंत्र दिवस",             "emoji": "🇮🇳", "day": 26, "month": 1,  "deity": "-",           "community": "National", "desc": "भारत का 76वाँ गणतंत्र दिवस"},

    # ── फरवरी ──
    {"name": "वसंत पंचमी",              "emoji": "🌼", "day": None,"month": 2,  "deity": "सरस्वती",     "community": "Hindu",    "desc": "माघ शुक्ल पंचमी (tithi-based)"},

    # ── मार्च ──
    {"name": "होली (धुलंडी)",            "emoji": "🎨", "day": None,"month": 3,  "deity": "कृष्ण-राधा",   "community": "Hindu",    "desc": "फाल्गुन पूर्णिमा के अगले दिन"},
    {"name": "उगादि / गुड़ी पड़वा",        "emoji": "🚩", "day": None,"month": 3,  "deity": "ब्रह्मा",      "community": "Regional", "desc": "चैत्र शुक्ल प्रतिपदा - तेलुगु/मराठी नववर्ष"},

    # ── अप्रैल ──
    {"name": "बैसाखी / वैसाखी",          "emoji": "🌾", "day": 13, "month": 4,  "deity": "वाहेगुरु",    "community": "Sikh",     "desc": "सिख नववर्ष एवं फसल उत्सव"},
    {"name": "बिहू (रंगाली)",             "emoji": "🎭", "day": 14, "month": 4,  "deity": "प्रकृति",      "community": "Regional", "desc": "असम का वसंत उत्सव"},
    {"name": "विशु",                    "emoji": "🌸", "day": 14, "month": 4,  "deity": "विष्णु",       "community": "Regional", "desc": "केरल का नववर्ष"},
    {"name": "तमिल नववर्ष (पुथांडु)",    "emoji": "🌺", "day": 14, "month": 4,  "deity": "सूर्यदेव",     "community": "Regional", "desc": "तमिल नववर्ष"},
    {"name": "अम्बेडकर जयंती",           "emoji": "🔵", "day": 14, "month": 4,  "deity": "-",           "community": "National", "desc": "डॉ. भीमराव अम्बेडकर जन्मदिन"},
    {"name": "महावीर जयंती",             "emoji": "🕊️", "day": None,"month": 4,  "deity": "महावीर स्वामी","community": "Jain",     "desc": "चैत्र शुक्ल त्रयोदशी (Jain)"},

    # ── मई ──
    {"name": "बुद्ध पूर्णिमा",            "emoji": "☸️",  "day": None,"month": 5,  "deity": "गौतम बुद्ध",  "community": "Buddhist", "desc": "वैशाख पूर्णिमा"},
    {"name": "परशुराम जयंती",            "emoji": "🪓", "day": None,"month": 5,  "deity": "परशुराम",      "community": "Hindu",    "desc": "वैशाख शुक्ल तृतीया"},

    # ── जून ──
    {"name": "जगन्नाथ रथ यात्रा",        "emoji": "🎡", "day": None,"month": 6,  "deity": "जगन्नाथ",     "community": "Hindu",    "desc": "आषाढ़ शुक्ल द्वितीया"},
    {"name": "Sant Kabir Jayanti",       "emoji": "📿", "day": None,"month": 6,  "deity": "निर्गुण ब्रह्म","community": "Hindu",    "desc": "ज्येष्ठ पूर्णिमा"},

    # ── अगस्त ──
    {"name": "स्वतंत्रता दिवस",           "emoji": "🇮🇳", "day": 15, "month": 8,  "deity": "-",           "community": "National", "desc": "भारत का स्वतंत्रता दिवस"},
    {"name": "पर्युषण पर्व",              "emoji": "🕊️", "day": None,"month": 8,  "deity": "जैन तीर्थंकर", "community": "Jain",     "desc": "जैन समाज का सबसे पवित्र पर्व"},
    {"name": "ओणम",                     "emoji": "🌺", "day": None,"month": 8,  "deity": "महाबली/विष्णु","community": "Regional", "desc": "केरल का प्रमुख त्यौहार (थिरुवोणम)"},

    # ── सितंबर ──
    {"name": "विश्वकर्मा पूजा",           "emoji": "🔧", "day": 17, "month": 9,  "deity": "विश्वकर्मा",   "community": "Hindu",    "desc": "सूर्य के कन्या राशि प्रवेश पर"},
    {"name": "सम्वत्सरी (Jain)",          "emoji": "🕊️", "day": None,"month": 9,  "deity": "जैन तीर्थंकर", "community": "Jain",     "desc": "जैन पर्युषण का अंतिम दिन - क्षमापना"},

    # ── अक्टूबर ──
    {"name": "गाँधी जयंती",              "emoji": "🕊️", "day": 2,  "month": 10, "deity": "-",           "community": "National", "desc": "महात्मा गाँधी जन्मदिन"},
    {"name": "नवरात्रि (शारदीय)",         "emoji": "🚩", "day": None,"month": 10, "deity": "दुर्गा",       "community": "Hindu",    "desc": "आश्विन शुक्ल प्रतिपदा"},

    # ── नवंबर ──
    {"name": "गुरु नानक जयंती",           "emoji": "🙏", "day": None,"month": 11, "deity": "गुरु नानक देव","community": "Sikh",     "desc": "कार्तिक पूर्णिमा - गुरुपर्व"},
    {"name": "बंदी छोड़ दिवस",            "emoji": "🕯️", "day": None,"month": 11, "deity": "गुरु हरगोविंद","community": "Sikh",     "desc": "दीपावली के दिन - सिख समाज"},

    # ── दिसंबर ──
    {"name": "क्रिसमस",                  "emoji": "🎄", "day": 25, "month": 12, "deity": "ईसा मसीह",    "community": "Christian","desc": "यीशु के जन्म का उत्सव"},

    # ── जैन विशेष ──
    {"name": "ऋषभदेव जयंती",             "emoji": "🕊️", "day": None,"month": 2,  "deity": "ऋषभदेव",      "community": "Jain",     "desc": "माघ कृष्ण त्रयोदशी"},
    {"name": "दीपावली (जैन - महावीर निर्वाण)","emoji": "🪔", "day": None,"month": 11, "deity": "महावीर स्वामी","community": "Jain",    "desc": "महावीर स्वामी के निर्वाण का दिन"},

    # ── सिख विशेष ──
    {"name": "गुरु गोविंद सिंह जयंती",    "emoji": "⚔️",  "day": None,"month": 1,  "deity": "गुरु गोविंद सिंह","community": "Sikh",  "desc": "पौष शुक्ल सप्तमी"},
    {"name": "होला मोहल्ला",              "emoji": "🏇", "day": None,"month": 3,  "deity": "वाहेगुरु",    "community": "Sikh",     "desc": "होली के अगले दिन - आनंदपुर साहिब"},

    # ── बौद्ध विशेष ──
    {"name": "धम्मचक्र प्रवर्तन दिवस",    "emoji": "☸️",  "day": 14, "month": 10, "deity": "गौतम बुद्ध",  "community": "Buddhist", "desc": "आश्विन पूर्णिमा - अशोक विजयदशमी"},
    {"name": "बुद्ध पूर्णिमा",             "emoji": "☸️",  "day": None,"month": 5,  "deity": "गौतम बुद्ध",  "community": "Buddhist", "desc": "वैशाख पूर्णिमा"},
]




def get_tithi_at_hour(date_obj, hour_float):
    """
    उस दिन के किसी भी खास समय (जैसे दोपहर 2 बजे) पर तिथि और पक्ष की गणना करता है।
    """
    jd_ut = swe.julday(date_obj.year, date_obj.month, date_obj.day, hour_float - 5.5)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    sun, _ = swe.calc_ut(jd_ut, swe.SUN, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
    moon, _ = swe.calc_ut(jd_ut, swe.MOON, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
    sun_lon = sun[0]
    moon_lon = moon[0]
    
    tithi_idx = int(((moon_lon - sun_lon) % 360) / 12.0)
    tithi_num = (tithi_idx % 15) + 1
    paksha = "S" if tithi_idx < 15 else "K"
    return tithi_num, paksha

def parse_panchang_date(panchang_data):
    """
    यूज़र द्वारा सेलेक्ट की गई तारीख को निकालता है ताकि हम उस दिन के अलग-अलग समय पर गणना कर सकें।
    """
    date_str = panchang_data.get('date_str', '')
    if date_str:
        clean_str = re.sub(r'\(.*?\)', '', date_str).strip()
        try:
            return datetime.datetime.strptime(clean_str, "%d %b %Y")
        except:
            pass
    return datetime.datetime.now(pytz.timezone("Asia/Kolkata"))

# ── Panchang Calculation ──────────────────────────────────────────
def get_today_panchang():
    try:
        now    = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
        dt_utc = now - datetime.timedelta(hours=5, minutes=30)
        jd_ut  = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0)
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

        return {
            "tithi":       tithi_num,
            "tithi_idx":   tithi_idx,
            "paksha":      paksha,
            "lunar_month": lunar_month_idx,   
        }
    except Exception as e:
        print(f"❌ Panchang error: {e}")
        return None

# ── Auto Time-Shift Festival Matching ─────────────────────────────────
def get_today_solar_festivals(date_obj=None):
    """Fixed/Solar date festivals check karo (Fix: Ab ye user ki selected date par kaam karega)"""
    if not date_obj:
        date_obj = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
    
    today_day   = date_obj.day
    today_month = date_obj.month
    matched = []
    for f in SOLAR_FESTIVALS:
        if f["day"] is None:
            continue
        if f["day"] == today_day and f["month"] == today_month:
            matched.append(f)
    return matched

def get_today_festivals(panchang_data=None):
    panchang = panchang_data if panchang_data else get_today_panchang()
    if not panchang: return []

    current_date = parse_panchang_date(panchang)
    
    # ... (आपका Tithi, Paksha, Month निकालने वाला पुराना कोड यहाँ रहने दें) ...
    # (लाइन 165 से 184 तक का कोड सेम रहेगा)
    
    p_tithi = panchang.get('tithi', 1)
    if isinstance(p_tithi, str):
        tithi_map = {"प्रतिपदा": 1, "द्वितीया": 2, "तृतीया": 3, "चतुर्थी": 4, "पंचमी": 5, "षष्ठी": 6, "सप्तमी": 7, "अष्टमी": 8, "नवमी": 9, "दशमी": 10, "एकादशी": 11, "द्वादशी": 12, "त्रयोदशी": 13, "चतुर्दशी": 14, "पूर्णिमा": 15, "अमावस्या": 15}
        clean_tithi = p_tithi.split()[0] if ' ' in p_tithi else p_tithi
        p_tithi = tithi_map.get(clean_tithi, 1)

    p_paksha = panchang.get('paksha', 'S')
    if isinstance(p_paksha, str):
        if "शुक्ल" in p_paksha: p_paksha = "S"
        elif "कृष्ण" in p_paksha: p_paksha = "K"

    p_month_idx = -1
    maas_str = panchang.get('hindu_maas', '')
    if isinstance(maas_str, str) and maas_str:
        for i, m in enumerate(LUNAR_MONTHS):
            if m in maas_str:
                p_month_idx = i + 1
                break
    if p_month_idx == -1:
        p_month = panchang.get('lunar_month', 0)
        p_month_idx = int(p_month) + 1

    slot_hours = {"predawn": 4.0, "afternoon": 14.0, "evening": 19.0, "midnight": 23.5}
    
    slot_cache = {}
    festivals = []
    
    for rule in FESTIVAL_RULES:
        if rule["month"] is not None and rule["month"] != p_month_idx:
            continue
            
        req_tithi = rule["tithi"]
        req_paksha = rule["paksha"]
        time_slot = rule.get("time_slot")
        
        if time_slot and time_slot in slot_hours:
            if time_slot not in slot_cache:
                slot_cache[time_slot] = get_tithi_at_hour(current_date, slot_hours[time_slot])
            calc_tithi, calc_paksha = slot_cache[time_slot]
            if req_tithi == calc_tithi and req_paksha == calc_paksha:
                festivals.append(rule)
        else:
            if req_tithi == p_tithi and req_paksha == p_paksha:
                festivals.append(rule)

    # 🚀 FIX: अब Solar (तारीख वाले) त्यौहार भी पंचांग लिस्ट में जुड़ेंगे!
    solar_festivals = get_today_solar_festivals(current_date)
    return festivals + solar_festivals

# ── Main Background Task ─────────────────────────────────────────────
def send_festival_notifications():
    print("\n" + "─" * 55)
    print("  🎊 Festival Notification Engine (AI-Powered)")
    print("─" * 55)

    panchang = get_today_panchang()
    if not panchang: return

    tithi_festivals = get_today_festivals(panchang)
    solar_festivals = get_today_solar_festivals()
    all_festivals   = tithi_festivals + solar_festivals

    if not all_festivals:
        print("  ℹ️  आज कोई विशेष पर्व नहीं है")
        return

    print(f"  🎉 आज के पर्व: {len(all_festivals)}")
    for f in all_festivals:
        print(f"     {f.get('emoji','')} {f['name']}")

    festival = all_festivals[0]
    print(f"\n  🔔 Main festival: {festival['emoji']} {festival['name']}")

    # Kundali calculation imports
    try:
        from daily_horoscope_engine import (
            calculate_natal_positions, calculate_lagna, build_dasha_info
        )
        ai_available = True
        print("  ✅ AI engine loaded")
    except Exception as e:
        print(f"  ⚠️ AI import failed: {e}")
        ai_available = False

    profiles = UserProfile.objects.select_related("user").all()
    sent = 0

    for profile in profiles:
        subs = PushSubscription.objects.filter(user=profile.user, is_active=True)
        if not subs.exists(): continue

        user_name = profile.user.first_name or profile.user.username
        community = festival.get("community", "Hindu")
        ai_msg = ""

        # AI-personalized remedy
        if ai_available and community in ["Hindu", "Jain", "Buddhist", "Sikh"]:
            try:
                kundali = SavedKundali.objects.filter(user=profile.user).order_by("created_at").first()
                if kundali:
                    natal_pos, natal_jd = calculate_natal_positions(kundali)
                    lagna_idx = calculate_lagna(natal_jd, kundali.lat, kundali.lon)
                    dasha = build_dasha_info(kundali)
                    prompt = build_festival_remedy_prompt(user_name, profile, festival, natal_pos, lagna_idx, dasha)
                    ai_msg = _call_gemini_festival(prompt)
                    if ai_msg:
                        print(f"  🤖 AI remedy generated for {user_name}")
            except Exception as e:
                print(f"  ⚠️ AI error for {user_name}: {e}")

        # Fallback message
        if not ai_msg:
            if community == "National":
                ai_msg = f"{user_name} जी, आज {festival.get('emoji','')} {festival['name']} है। जय हिंद! 🇮🇳"
            elif community in ["Sikh", "Jain", "Buddhist", "Christian"]:
                ai_msg = f"{user_name} जी, {festival.get('emoji','')} {festival['name']} की हार्दिक शुभकामनाएं! इस पावन अवसर पर आपके जीवन में सुख-शांति आए। 🙏"
            else:
                deity = festival.get("deity", "भगवान")
                ai_msg = f"{user_name} जी, आज {festival['name']} पर {deity} की विशेष पूजा करें। यह दिन आपके लिए शुभ फलदायी हो। 🙏"

        # UserNotification mein save karo
        try:
            UserNotification.objects.create(
                user=profile.user,
                title=f"{festival.get('emoji','')} {festival['name']} की शुभकामनाएं!",
                message=ai_msg,
                notification_type="FESTIVAL"
            )
        except Exception as e:
            print(f"  ⚠️ Notification save error: {e}")

        # Push notification bhejo
        preview = ai_msg[:100] + "..."
        send_push_to_user(
            profile.user,
            f"{festival.get('emoji','')} {festival['name']} की शुभकामनाएं!",
            preview,
            "/?tab=view-notifications"
        )
        sent += 1

    print(f"\n  📲 Total sent: {sent}")
    print("─" * 55)

if __name__ == "__main__":
    send_festival_notifications()