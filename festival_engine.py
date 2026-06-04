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

from core.models import UserProfile, PushSubscription
from core.views.push_views import send_push_to_user

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
def get_today_festivals(panchang_data=None):
    panchang = panchang_data if panchang_data else get_today_panchang()
    if not panchang: return []

    current_date = parse_panchang_date(panchang)

    # 1. Tithi (हिंदी को नंबर में बदलें)
    p_tithi = panchang.get('tithi', 1)
    if isinstance(p_tithi, str):
        tithi_map = {"प्रतिपदा": 1, "द्वितीया": 2, "तृतीया": 3, "चतुर्थी": 4, "पंचमी": 5, "षष्ठी": 6, "सप्तमी": 7, "अष्टमी": 8, "नवमी": 9, "दशमी": 10, "एकादशी": 11, "द्वादशी": 12, "त्रयोदशी": 13, "चतुर्दशी": 14, "पूर्णिमा": 15, "अमावस्या": 15}
        clean_tithi = p_tithi.split()[0] if ' ' in p_tithi else p_tithi
        p_tithi = tithi_map.get(clean_tithi, 1)

    # 2. Paksha (पक्ष को S/K में बदलें)
    p_paksha = panchang.get('paksha', 'S')
    if isinstance(p_paksha, str):
        if "शुक्ल" in p_paksha: p_paksha = "S"
        elif "कृष्ण" in p_paksha: p_paksha = "K"

    # 3. Month (महीने का नंबर निकालें)
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

    # समय के स्लॉट्स (Hours in 24h format)
    slot_hours = {
        "predawn": 4.0,   # सुबह 4 बजे
        "afternoon": 14.0, # दोपहर 2 बजे
        "evening": 19.0,   # शाम 7 बजे
        "midnight": 23.5   # रात 11:30 बजे
    }
    
    # 4. मैच करें (Dynamic Checking)
    slot_cache = {}
    festivals = []
    
    for rule in FESTIVAL_RULES:
        # अगर महीना ही मैच नहीं हो रहा, तो फालतू में कैलकुलेशन ना करें (Speed Optimization)
        if rule["month"] is not None and rule["month"] != p_month_idx:
            continue
            
        req_tithi = rule["tithi"]
        req_paksha = rule["paksha"]
        time_slot = rule.get("time_slot")
        
        # अगर त्योहार का कोई खास 'कर्म काल' है, तो बैकग्राउंड में उसी समय की तिथि निकालें
        if time_slot and time_slot in slot_hours:
            if time_slot not in slot_cache:
                slot_cache[time_slot] = get_tithi_at_hour(current_date, slot_hours[time_slot])
            
            calc_tithi, calc_paksha = slot_cache[time_slot]
            if req_tithi == calc_tithi and req_paksha == calc_paksha:
                festivals.append(rule)
        else:
            # वरना नॉर्मल सुबह वाली 'उदया तिथि' से ही चेक कर लें
            if req_tithi == p_tithi and req_paksha == p_paksha:
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

        send_push_to_user(profile.user, f"{festival['emoji']} {festival['name']} की शुभकामनाएं!", preview, "/?tab=view-panchang")
        sent += 1

    print(f"  📲 Sent: {sent}")
    print("─" * 55)

if __name__ == "__main__":
    send_festival_notifications()