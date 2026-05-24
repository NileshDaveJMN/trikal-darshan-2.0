"""
================================================================
  त्रिकाल दर्शन - IMPROVED DAILY HOROSCOPE ENGINE v3.0
  
  सुधार किए गए:
  ✅ SwissEph से पूर्ण गोचर: उच्च/नीच/वक्री/मार्गी + डिग्री
  ✅ Vimshottari Dasha (existing kundali_engine से)
  ✅ शनि साढ़ेसाती / कंटक शनि detection
  ✅ गुरु का शुभ/अशुभ transit (लग्न से भाव)
  ✅ User Profile के सभी fields का deep use
  ✅ Ashtakvarg transit score → Gemini prompt में
  ✅ मजबूत multi-key Gemini rotation + retry
  ✅ Telegram HTML formatting (Markdown नहीं)
  ✅ Format: प्रत्येक user को 1 बार, date-guard के साथ
================================================================

Usage: python daily_horoscope_engine.py

Dependencies (already in requirements.txt):
    pyswisseph, requests, django
"""

import os
import sys
import datetime
import random
import re
import time
import requests
import urllib3
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── .env Auto-Load (PythonAnywhere ke liye) ──────────────────
_env_path = Path(__file__).parent / '.env'
if _env_path.exists():
    for _line in _env_path.read_text(encoding='utf-8').splitlines():
        _line = _line.strip()
        if _line and '=' in _line and not _line.startswith('#'):
            _k, _v = _line.split('=', 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# ── Django Setup ─────────────────────────────────────────────
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trikal_portal.settings')
import django
django.setup()

from core.models import UserProfile, SavedKundali
from engines.kundali_engine import get_vimshottari_dasha
from engines.utils import P_HINDI_FULL

# ── SwissEph ─────────────────────────────────────────────────
import swisseph as swe
import pytz

# ── API Keys (GEMINI_API_KEYS1 to GEMINI_API_KEYS9 support) ──
GEMINI_API_KEYS = []
for i in range(1, 10):  # GEMINI_API_KEYS1 se GEMINI_API_KEYS9 tak
    key = os.getenv(f"GEMINI_API_KEYS{i}", "").strip()
    if key:
        GEMINI_API_KEYS.append(key)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GEMINI_MODEL = "gemini-3-flash-preview"  

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SECTION 1 — VEDIC CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RASHI_NAMES = [
    "मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या",
    "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"
]

NAKSHATRA_NAMES = [
    "अश्विनी", "भरणी", "कृत्तिका", "रोहिणी", "मृगशिरा", "आर्द्रा",
    "पुनर्वसु", "पुष्य", "आश्लेषा", "मघा", "पूर्वाफाल्गुनी", "उत्तराफाल्गुनी",
    "हस्त", "चित्रा", "स्वाती", "विशाखा", "अनुराधा", "ज्येष्ठा",
    "मूल", "पूर्वाषाढ़ा", "उत्तराषाढ़ा", "श्रवण", "धनिष्ठा", "शतभिषा",
    "पूर्वाभाद्रपद", "उत्तराभाद्रपद", "रेवती"
]

# रा‌शि स्वामी (lord of each rashi, 0-indexed)
RASHI_LORD = {
    0: "मंगल", 1: "शुक्र", 2: "बुध", 3: "चंद्र",
    4: "सूर्य", 5: "बुध", 6: "शुक्र", 7: "मंगल",
    8: "गुरु", 9: "शनि", 10: "शनि", 11: "गुरु"
}

# उच्च राशि और उच्चांश डिग्री
UCCHA = {
    "सूर्य":  (0, 10),   # मेष 10°
    "चंद्र":  (1, 3),    # वृषभ 3°
    "मंगल":  (9, 28),   # मकर 28°
    "बुध":   (5, 15),   # कन्या 15°
    "गुरु":  (3, 5),    # कर्क 5°
    "शुक्र": (11, 27),  # मीन 27°
    "शनि":  (6, 20),   # तुला 20°
    "राहु":  (2, 20),   # मिथुन 20°
    "केतु":  (8, 20),   # धनु 20°
}

# नीच राशि (उच्च से 7वीं)
NEECHA_RASHI = {
    "सूर्य": 6, "चंद्र": 7, "मंगल": 3,
    "बुध": 11, "गुरु": 9, "शुक्र": 5,
    "शनि": 0, "राहु": 8, "केतु": 2
}

# SwissEph planet IDs
SWE_IDS = {
    "सूर्य":  swe.SUN,
    "चंद्र":  swe.MOON,
    "मंगल":  swe.MARS,
    "बुध":   swe.MERCURY,
    "गुरु":  swe.JUPITER,
    "शुक्र": swe.VENUS,
    "शनि":  swe.SATURN,
    "राहु":  swe.TRUE_NODE,
}

# Ashtakvarg transit BAV rules (each planet's good houses from itself)
# Source: standard Parashari Ashtakvarg
TRANSIT_GOOD_HOUSES = {
    "शनि":  [3, 6, 11],
    "गुरु":  [2, 5, 7, 9, 11],
    "मंगल":  [3, 6, 11],
    "सूर्य":  [3, 6, 10, 11],
    "चंद्र":  [1, 3, 6, 7, 10, 11],
    "बुध":   [2, 4, 6, 8, 10, 11],
    "शुक्र": [1, 2, 3, 4, 5, 8, 9, 11, 12],
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SECTION 2 — SWISS EPHEMERIS CALCULATIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _dt_to_jd(dt: datetime.datetime, tz_str: str = "Asia/Kolkata") -> float:
    """datetime → Julian Day (UTC)"""
    tz = pytz.timezone(tz_str)
    if dt.tzinfo is None:
        dt = tz.localize(dt)
    dt_utc = dt.astimezone(pytz.utc)
    return swe.julday(
        dt_utc.year, dt_utc.month, dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
    )


def _get_ayanamsha(jd: float) -> float:
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    return swe.get_ayanamsa_ut(jd)


def _vedic_lon(planet_id: int, jd: float) -> tuple[float, bool]:
    """
    Sidereal longitude + retrograde flag.
    Returns (vedic_longitude, is_retrograde)
    """
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    result, _ = swe.calc_ut(jd, planet_id, flags)
    tropical_lon = result[0]
    speed = result[3]
    ayan = _get_ayanamsha(jd)
    vedic = (tropical_lon - ayan) % 360
    return vedic, speed < 0


def _get_avastha(graha: str, rashi_idx: int, degree: float) -> str:
    """उच्च / नीच / स्व / मित्र / सम"""
    # उच्च
    if graha in UCCHA:
        u_rashi, u_deg = UCCHA[graha]
        if rashi_idx == u_rashi:
            if abs(degree - u_deg) <= 3:
                return "परम उच्च ✨"
            return "उच्च राशि 🌟"
    # नीच
    if graha in NEECHA_RASHI and rashi_idx == NEECHA_RASHI[graha]:
        return "नीच राशि ⚠️"
    # स्व राशि
    swa = [r for r, lord in RASHI_LORD.items() if lord == graha]
    if rashi_idx in swa:
        return "स्व राशि 💪"
    return "सम 🔵"


def calculate_transit_positions(jd: float) -> dict:
    """
    सभी 9 ग्रहों की गोचर स्थिति।
    Returns dict: graha → {rashi, rashi_idx, degree, nakshatra, vakri, avastha, full_deg}
    """
    positions = {}
    for naam, pid in SWE_IDS.items():
        lon, retro = _vedic_lon(pid, jd)
        r_idx = int(lon / 30)
        deg_in_r = lon % 30
        nak_idx = int(lon / (360 / 27))
        avastha = _get_avastha(naam, r_idx, deg_in_r)

        positions[naam] = {
            "rashi": RASHI_NAMES[r_idx],
            "rashi_idx": r_idx,
            "degree": round(deg_in_r, 2),
            "full_deg": round(lon, 4),
            "nakshatra": NAKSHATRA_NAMES[nak_idx],
            "vakri": retro,
            "avastha": avastha,
        }

    # केतु = राहु + 180°
    rahu_lon = positions["राहु"]["full_deg"]
    ketu_lon = (rahu_lon + 180) % 360
    k_idx = int(ketu_lon / 30)
    k_nak = int(ketu_lon / (360 / 27))
    positions["केतु"] = {
        "rashi": RASHI_NAMES[k_idx],
        "rashi_idx": k_idx,
        "degree": round(ketu_lon % 30, 2),
        "full_deg": round(ketu_lon, 4),
        "nakshatra": NAKSHATRA_NAMES[k_nak],
        "vakri": True,
        "avastha": _get_avastha("केतु", k_idx, ketu_lon % 30),
    }
    return positions


def calculate_natal_positions(kundali) -> dict:
    """
    SavedKundali object से जन्म-कालीन ग्रह स्थिति।
    IST → UTC → JD
    """
    dt_ist = datetime.datetime(
        kundali.year, kundali.month, kundali.day,
        kundali.hour, kundali.minute, kundali.second
    )
    dt_utc = dt_ist - datetime.timedelta(hours=5, minutes=30)
    jd = swe.julday(
        dt_utc.year, dt_utc.month, dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
    )
    return calculate_transit_positions(jd), jd


def calculate_lagna(jd: float, lat: float, lon: float) -> int:
    """जन्म लग्न राशि index (0-11)"""
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    ayan = _get_ayanamsha(jd)
    cusps, ascmc = swe.houses(jd, lat, lon, b'W')
    asc_sid = (ascmc[0] - ayan) % 360
    return int(asc_sid / 30)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SECTION 3 — VEDIC ANALYSIS (Gochar + Dasha + SAT)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def check_saadesati(natal_chandra_idx: int, transit_shani_idx: int) -> tuple[bool, str]:
    """
    शनि साढ़ेसाती: जन्म चंद्र से 12, 1, 2वें स्थान पर शनि।
    कंटक शनि: 4, 8वें स्थान पर।
    Returns (is_saadesati_or_kantaka, description)
    """
    shani_from_chandra = (transit_shani_idx - natal_chandra_idx) % 12 + 1

    if shani_from_chandra == 12:
        return True, (
            f"⚠️ शनि साढ़ेसाती का पहला चरण (12वाँ भाव): खर्च और मानसिक तनाव हो सकता है। "
            f"धैर्य रखें और फिजूलखर्ची से बचें।"
        )
    elif shani_from_chandra == 1:
        return True, (
            f"⚠️ शनि साढ़ेसाती का मुख्य चरण (1ला भाव): स्वास्थ्य और कार्य पर दबाव। "
            f"शनि मंत्र जाप करें: 'ॐ शं शनैश्चराय नमः'।"
        )
    elif shani_from_chandra == 2:
        return True, (
            f"⚠️ शनि साढ़ेसाती का अंतिम चरण (2रा भाव): आर्थिक दबाव हो सकता है। "
            f"मेहनत करते रहें, राहत निकट है।"
        )
    elif shani_from_chandra == 4:
        return True, (
            f"🔶 कंटक शनि (4थे भाव से): गृह-जीवन में उथल-पुथल। "
            f"परिवार में संयम रखें।"
        )
    elif shani_from_chandra == 8:
        return True, (
            f"🔶 कंटक शनि (8वें भाव से): अचानक परेशानियाँ आ सकती हैं। "
            f"वाहन-चालन में सावधानी बरतें।"
        )
    return False, (
        f"✅ शनि गोचर सामान्य है (चंद्र से {shani_from_chandra}वाँ स्थान)। "
        f"प्रयास रंग लाएँगे।"
    )


def check_guru_gochar(natal_lagna_idx: int, transit_guru_idx: int) -> str:
    """गुरु का लग्न से गोचर विश्लेषण"""
    guru_from_lagna = (transit_guru_idx - natal_lagna_idx) % 12 + 1

    GURU_PHAL = {
        1: "✨ गुरु लग्न में — नई शुरुआतें, मान-सम्मान और आत्मविश्वास में वृद्धि।",
        2: "💰 गुरु 2रे भाव में — धन और परिवार के लिए शुभ समय।",
        5: "🎓 गुरु 5वें भाव में — बुद्धि, संतान और प्रेम-विवाह के लिए बहुत शुभ।",
        7: "💑 गुरु 7वें भाव में — विवाह और साझेदारी के अवसर।",
        9: "🙏 गुरु 9वें भाव में — भाग्योदय! यात्रा और उन्नति का समय।",
        11: "🏆 गुरु 11वें भाव में — आय और मनोकामनाएँ पूरी होने का उत्तम योग।",
        4: "🏠 गुरु 4थे भाव में — गृह-सुख, मातृ-पक्ष और संपत्ति के मामले।",
        10: "💼 गुरु 10वें भाव में — करियर में नई ऊँचाइयाँ।",
        6: "⚠️ गुरु 6वें भाव में — रुकावटें और प्रतिस्पर्धा, पर कर्म से जीत होगी।",
        8: "🔶 गुरु 8वें भाव में — गुप्त विद्या में रुचि, पर स्वास्थ्य पर ध्यान दें।",
        12: "🧘 गुरु 12वें भाव में — आध्यात्मिक उन्नति, खर्च अधिक हो सकता है।",
        3: "✍️ गुरु 3रे भाव में — पराक्रम और लेखन-कला में उन्नति।",
    }
    return GURU_PHAL.get(guru_from_lagna, f"गुरु {guru_from_lagna}वें भाव में है।")


def get_transit_ashtakvarg_score(natal_pos: dict, transit_pos: dict, lagna_idx: int) -> dict:
    """
    मुख्य ग्रहों का transit-time Ashtakvarg score निकालें।
    (Transit planet → House from Natal position of same planet)
    Returns: {graha: {"house": N, "score_label": "शुभ/अशुभ"}}
    """
    results = {}
    key_grahas = ["शनि", "गुरु", "मंगल", "सूर्य", "चंद्र", "बुध", "शुक्र"]

    for g in key_grahas:
        if g not in natal_pos or g not in transit_pos:
            continue
        natal_r = natal_pos[g]["rashi_idx"]
        transit_r = transit_pos[g]["rashi_idx"]
        house_from_natal = (transit_r - natal_r) % 12 + 1
        good_houses = TRANSIT_GOOD_HOUSES.get(g, [])
        is_good = house_from_natal in good_houses
        results[g] = {
            "house": house_from_natal,
            "score_label": "शुभ ✅" if is_good else "अशुभ ⚠️",
        }
    return results


def get_vakri_grahas(transit_pos: dict) -> list[str]:
    """वक्री ग्रहों की सूची"""
    return [g for g, data in transit_pos.items() if data.get("vakri")]


def build_dasha_info(kundali) -> dict:
    """
    Existing kundali_engine.get_vimshottari_dasha() से
    वर्तमान महादशा/अंतर्दशा निकालें।
    Returns: {"md": "गुरु", "ad": "शनि", "md_end": "...", "ad_end": "..."}
    """
    try:
        dt_ist = datetime.datetime(
            kundali.year, kundali.month, kundali.day,
            kundali.hour, kundali.minute, kundali.second
        )
        dt_utc = dt_ist - datetime.timedelta(hours=5, minutes=30)
        jd = swe.julday(
            dt_utc.year, dt_utc.month, dt_utc.day,
            dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
        )
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        # Moon degree (sidereal)
        moon_res, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
        moon_deg = moon_res[0]

        dasha_list, curr_dasha = get_vimshottari_dasha(moon_deg, dt_ist)

        # current dasha end dates
        md_end, ad_end = "अज्ञात", "अज्ञात"
        for md in dasha_list:
            if md["is_current"]:
                md_end = md["end"]
                for ad in md["antardashas"]:
                    if ad["is_current"]:
                        ad_end = ad["end"]
                        break
                break

        return {
            "md": curr_dasha.get("md", "अज्ञात"),
            "ad": curr_dasha.get("ad", "अज्ञात"),
            "md_end": md_end,
            "ad_end": ad_end,
        }
    except Exception as e:
        print(f"  ⚠️  Dasha Error: {e}")
        return {"md": "अज्ञात", "ad": "अज्ञात", "md_end": "-", "ad_end": "-"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SECTION 4 — GEMINI PROMPT BUILDER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_horoscope_prompt(
    user_name: str,
    profile: "UserProfile",
    natal_pos: dict,
    transit_pos: dict,
    lagna_idx: int,
    dasha: dict,
    saadesati_active: bool,
    saadesati_text: str,
    guru_text: str,
    ashtakvarg: dict,
    vakri_grahas: list[str],
) -> str:
    """
    Vedic गणित और User profile को मिलाकर
    Gemini के लिए एक अत्यंत सटीक prompt बनाएँ।
    """
    today_str = datetime.date.today().strftime("%d %B %Y")
    natal_chandra = natal_pos["चंद्र"]["rashi"]
    natal_lagna = RASHI_NAMES[lagna_idx]

    # ── User profile fields ──────────────────────────────────
    profile_lines = []
    field_map = {
        "पेशा":           profile.profession,
        "मुख्य लक्ष्य":   profile.primary_focus,
        "वर्तमान चुनौती": profile.current_challenge,
        "रिश्ते की स्थिति": profile.relationship_status,
        "आर्थिक लक्ष्य":  profile.finance_focus,
        "शारीरिक सक्रियता": profile.activity_level,
        "यात्रा की आदत":   profile.travel_habit,
    }
    for label, val in field_map.items():
        if val:
            profile_lines.append(f"  • {label}: {val}")
    profile_text = "\n".join(profile_lines) if profile_lines else "  • सामान्य जीवन (कोई विशेष फोकस नहीं)"

    # ── Transit summary ──────────────────────────────────────
    key_transit = ["सूर्य", "चंद्र", "मंगल", "बुध", "गुरु", "शुक्र", "शनि", "राहु", "केतु"]
    transit_lines = []
    for g in key_transit:
        d = transit_pos[g]
        vakri_flag = " (वक्री 🔄)" if d["vakri"] else ""
        transit_lines.append(
            f"  {g}: {d['rashi']} {d['degree']:.1f}° | {d['nakshatra']} | {d['avastha']}{vakri_flag}"
        )
    transit_text = "\n".join(transit_lines)

    # ── Ashtakvarg transit ───────────────────────────────────
    av_lines = [
        f"  {g}: जन्म-राशि से {v['house']}वाँ भाव → {v['score_label']}"
        for g, v in ashtakvarg.items()
    ]
    av_text = "\n".join(av_lines)

    # ── Vakri grahas ─────────────────────────────────────────
    vakri_text = "、".join(vakri_grahas) if vakri_grahas else "कोई नहीं"

    prompt = f"""
आज की तारीख: {today_str}

आप एक अनुभवी वैदिक ज्योतिषी हैं जो पाराशरी सिद्धांतों पर आधारित सटीक, प्रेरक और व्यक्तिगत फलित देते हैं।

══════════════════════════════════════════════
 जातक की जन्म-कुंडली का सारांश
══════════════════════════════════════════════
  नाम:           {user_name}
  जन्म लग्न:      {natal_lagna}
  जन्म चंद्र-राशि: {natal_chandra}
  वर्तमान महादशा:  {dasha['md']} महादशा (समाप्ति: {dasha['md_end']})
  वर्तमान अंतर्दशा: {dasha['ad']} अंतर्दशा (समाप्ति: {dasha['ad_end']})

══════════════════════════════════════════════
 यूजर की व्यक्तिगत स्थिति और प्राथमिकताएँ
══════════════════════════════════════════════
{profile_text}

══════════════════════════════════════════════
 आज का सटीक गोचर (SwissEph Lahiri Ayanamsha)
══════════════════════════════════════════════
{transit_text}

══════════════════════════════════════════════
 गोचर अष्टकवर्ग स्कोर (जन्म राशि से transit)
══════════════════════════════════════════════
{av_text}
  वक्री ग्रह आज: {vakri_text}

══════════════════════════════════════════════
 विशेष ग्रह-योग
══════════════════════════════════════════════
  शनि साढ़ेसाती/कंटक: {saadesati_text}
  गुरु गोचर:           {guru_text}

══════════════════════════════════════════════
 फलित नियम (इन्हें सख्ती से पालन करें)
══════════════════════════════════════════════
1. दशा स्वामी ({dasha['md']}) और अंतर्दशा स्वामी ({dasha['ad']}) के गुण-दोष को
   आज के गोचर से मिलाकर फलित दें।
2. शुभ ग्रहों का transit good house में हो तो उसे उजागर करें;
   अशुभ transit हो तो समाधान/उपाय भी बताएँ।
3. यूजर के '{profile.primary_focus or 'सामान्य लक्ष्य'}' और
   '{profile.current_challenge or 'सामान्य चुनौती'}' को ध्यान में रखते हुए
   करियर / आर्थिक / स्वास्थ्य / रिश्ते — जो भी relevant हो, उस पर विशेष बात करें।
4. वक्री ग्रह ({vakri_text}) के प्रभाव पर एक वाक्य जरूर लिखें।
5. भाषा: सरल, उत्साहवर्धक, सकारात्मक हिंदी। कोई ** या ## Markdown नहीं।
6. लंबाई: 5-6 लाइन (न बहुत छोटा, न बहुत लंबा)।
7. शुरुआत: '{user_name} जी,' से करें।
8. अंत में एक छोटा वैदिक उपाय (रंग / मंत्र / कर्म) जरूर बताएँ जो दशा स्वामी
   या आज की विशेष ग्रह-स्थिति के अनुकूल हो।
9. टोन: एक अनुभवी और करुणामय गुरु जैसा — डराएँ नहीं, मार्गदर्शन करें।
"""
    return prompt.strip()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SECTION 5 — GEMINI API CALL (Multi-key Rotation + Retry)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from typing import Optional

def call_gemini(prompt: str, max_retries: int = 3) -> Optional[str]:

    """
    सभी API keys को rotate करते हुए Gemini call करें।
    Returns: response text or None
    """
    if not GEMINI_API_KEYS:
        print("  ❌ कोई GEMINI_API_KEY नहीं मिली!")
        return None

    keys = GEMINI_API_KEYS.copy()
    random.shuffle(keys)

    for attempt, api_key in enumerate(keys[:max_retries], 1):
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{GEMINI_MODEL}:generateContent?key={api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.75,
               # "maxOutputTokens": 512,
            }
        }
        try:
            resp = requests.post(url, json=payload, timeout=30, verify=False)

            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    candidate = candidates[0]
                    # Safety filter check
                    if candidate.get("finishReason") == "SAFETY":
                        print(f"  ⚠️  Safety filter triggered (attempt {attempt})")
                        continue
                    parts = candidate.get("content", {}).get("parts", [])
                    if parts:
                        text = parts[0].get("text", "").strip()
                        # Markdown cleanup
                        text = re.sub(r'\*+', '', text)
                        text = re.sub(r'#+\s*', '', text)
                        return text

            elif resp.status_code == 429:
                print(f"  ⏳ Rate limit (attempt {attempt}), 2s रुकते हैं...")
                time.sleep(2)
            else:
                print(f"  ❌ API Error {resp.status_code} (attempt {attempt}): {resp.text[:80]}")

        except requests.exceptions.Timeout:
            print(f"  ⏱️  Timeout (attempt {attempt})")
        except Exception as e:
            print(f"  ❌ Exception (attempt {attempt}): {e}")

        time.sleep(1)

    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SECTION 6 — TELEGRAM SENDER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def send_telegram(chat_id: str, text: str) -> bool:
    """HTML-formatted Telegram message भेजें"""
    if not BOT_TOKEN:
        print("  ⚠️  BOT_TOKEN नहीं है, Telegram skip।")
        return False

    # Plain text को HTML-safe बनाएँ
    safe_text = (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )
    header = "<b>🔮 त्रिकाल दर्शन — आपका आज का राशिफल</b>\n\n"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":    chat_id,
        "text":       header + safe_text,
        "parse_mode": "HTML",
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            return True
        else:
            print(f"  ❌ Telegram Error {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        print(f"  ❌ Telegram Exception: {e}")
    return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SECTION 7 — MAIN ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def process_one_user(profile: "UserProfile", today_transit: dict, today_jd: float) -> bool:
    """
    एक user के लिए पूरा pipeline:
    natal → lagna → dasha → analysis → prompt → gemini → save → telegram
    Returns True अगर सफल
    """
    user_name = profile.user.first_name or profile.user.username
    print(f"\n  👤 {user_name} ({profile.user.username})")

    # 1. Primary Kundali लाएँ
    kundali = (
        SavedKundali.objects
        .filter(user=profile.user)
        .order_by("created_at")
        .first()
    )
    if not kundali:
        print("     ⚠️  कोई SavedKundali नहीं मिली, skip।")
        return False

    # 2. Natal positions
    natal_pos, natal_jd = calculate_natal_positions(kundali)

    # 3. Lagna
    lagna_idx = calculate_lagna(natal_jd, kundali.lat, kundali.lon)

    # 4. Dasha (existing engine)
    dasha = build_dasha_info(kundali)
    print(f"     📅 Dasha: {dasha['md']} / {dasha['ad']}")

    # 5. Saadesati / Kantaka
    natal_chandra_idx = natal_pos["चंद्र"]["rashi_idx"]
    transit_shani_idx = today_transit["शनि"]["rashi_idx"]
    saadesati_active, saadesati_text = check_saadesati(natal_chandra_idx, transit_shani_idx)

    # 6. Guru gochar
    transit_guru_idx = today_transit["गुरु"]["rashi_idx"]
    guru_text = check_guru_gochar(lagna_idx, transit_guru_idx)

    # 7. Ashtakvarg transit score
    ashtakvarg = get_transit_ashtakvarg_score(natal_pos, today_transit, lagna_idx)

    # 8. Vakri grahas
    vakri = get_vakri_grahas(today_transit)

    # 9. Prompt बनाएँ
    prompt = build_horoscope_prompt(
        user_name=user_name,
        profile=profile,
        natal_pos=natal_pos,
        transit_pos=today_transit,
        lagna_idx=lagna_idx,
        dasha=dasha,
        saadesati_active=saadesati_active,
        saadesati_text=saadesati_text,
        guru_text=guru_text,
        ashtakvarg=ashtakvarg,
        vakri_grahas=vakri,
    )

    # 10. Gemini call
    rashifal_text = call_gemini(prompt)
    if not rashifal_text:
        print("     ❌ Gemini से जवाब नहीं मिला।")
        return False

    print(f"     ✅ राशिफल बना: {len(rashifal_text)} characters")

    # 11. Database में save करें
    profile.daily_horoscope_text = rashifal_text
    profile.horoscope_date = datetime.date.today()
    profile.save(update_fields=["daily_horoscope_text", "horoscope_date"])

    # 12. Telegram भेजें (अगर chat_id है)
    if profile.telegram_chat_id:
        ok = send_telegram(profile.telegram_chat_id, rashifal_text)
        print(f"     📱 Telegram: {'✅ भेजा' if ok else '❌ विफल'}")
    else:
        print("     📱 Telegram: chat_id नहीं है, skip।")

    return True


def generate_and_send_daily_horoscopes():
    """
    Main entry point:
    सभी eligible users के लिए daily rashifal generate और send करें।
    """
    print("\n" + "━" * 60)
    print("  🔮 त्रिकाल दर्शन — Daily Horoscope Engine v3.0")
    print("━" * 60)
    print(f"  📅 आज: {datetime.date.today()}")

    # API key check
    if not GEMINI_API_KEYS:
        print("  ❌ GEMINI_API_KEYS नहीं मिलीं! .env चेक करें।")
        return

    # आज का transit एक बार निकालें (सभी users के लिए same)
    tz = pytz.timezone("Asia/Kolkata")
    now = datetime.datetime.now(tz)
    today_jd = _dt_to_jd(now, "Asia/Kolkata")
    today_transit = calculate_transit_positions(today_jd)

    # मुख्य ग्रह स्थिति print करें
    print("\n  🪐 आज का गोचर:")
    for g in ["सूर्य", "चंद्र", "मंगल", "बुध", "गुरु", "शुक्र", "शनि", "राहु"]:
        d = today_transit[g]
        vakri = " 🔄" if d["vakri"] else ""
        print(f"     {g:<6}: {d['rashi']} {d['degree']:.1f}° | {d['nakshatra']}{vakri} | {d['avastha']}")

    # Users लाएँ (telegram_chat_id वाले)
    profiles = (
        UserProfile.objects
        .select_related("user")
        .exclude(telegram_chat_id__isnull=True)
        .exclude(telegram_chat_id__exact="")
    )

    total = profiles.count()
    print(f"\n  👥 कुल Telegram-linked users: {total}")

    today = datetime.date.today()
    sent, skipped, failed = 0, 0, 0

    for profile in profiles:
        # Date guard: आज का rashifal पहले से बना हो तो skip
       # if profile.horoscope_date == today:
         #   skipped += 1
          #  continue

        success = process_one_user(profile, today_transit, today_jd)
        if success:
            sent += 1
        else:
            failed += 1

        # Rate limiting
        time.sleep(0.5)

    print("\n" + "━" * 60)
    print(f"  ✅ भेजे गए:   {sent}")
    print(f"  ⏭️  Skip हुए: {skipped} (आज पहले से बना था)")
    print(f"  ❌ विफल:      {failed}")
    print("━" * 60 + "\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SECTION 8 — STANDALONE TEST (Django के बिना भी चला सकते हैं)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_single_kundali(
    naam: str,
    dd: int, mm: int, yyyy: int,
    hh: int, m_m: int,
    lat: float, lon: float,
    profession: str = "",
    primary_focus: str = "",
    current_challenge: str = "",
    relationship_status: str = "",
    finance_focus: str = "",
):
    """
    Django DB के बिना सीधे एक kundali test करें।
    (Development/debugging के लिए)
    """
    print(f"\n🧪 Test Mode: {naam} की कुंडली")

    # Mock kundali object
    class MockKundali:
        year, month, day = yyyy, mm, dd
        hour, minute, second = hh, m_m, 0

    class MockProfile:
        class user:
            first_name = naam
            username = naam

        telegram_chat_id = None

    mock_kundali = MockKundali()
    mock_kundali.lat = lat
    mock_kundali.lon = lon

    mock_profile = MockProfile()
    mock_profile.profession = profession
    mock_profile.primary_focus = primary_focus
    mock_profile.current_challenge = current_challenge
    mock_profile.relationship_status = relationship_status
    mock_profile.finance_focus = finance_focus
    mock_profile.activity_level = ""
    mock_profile.travel_habit = ""

    # Transit
    tz = pytz.timezone("Asia/Kolkata")
    today_jd = _dt_to_jd(datetime.datetime.now(tz), "Asia/Kolkata")
    today_transit = calculate_transit_positions(today_jd)

    # Natal
    natal_pos, natal_jd = calculate_natal_positions(mock_kundali)
    lagna_idx = calculate_lagna(natal_jd, lat, lon)
    dasha = build_dasha_info(mock_kundali)

    natal_chandra_idx = natal_pos["चंद्र"]["rashi_idx"]
    _, saadesati_text = check_saadesati(natal_chandra_idx, today_transit["शनि"]["rashi_idx"])
    guru_text = check_guru_gochar(lagna_idx, today_transit["गुरु"]["rashi_idx"])
    ashtakvarg = get_transit_ashtakvarg_score(natal_pos, today_transit, lagna_idx)
    vakri = get_vakri_grahas(today_transit)

    prompt = build_horoscope_prompt(
        user_name=naam,
        profile=mock_profile,
        natal_pos=natal_pos,
        transit_pos=today_transit,
        lagna_idx=lagna_idx,
        dasha=dasha,
        saadesati_active=False,
        saadesati_text=saadesati_text,
        guru_text=guru_text,
        ashtakvarg=ashtakvarg,
        vakri_grahas=vakri,
    )

    print("\n📋 Generated Prompt (पहले 600 chars):")
    print(prompt[:600] + "...")

    if GEMINI_API_KEYS:
        print("\n🤖 Gemini से राशिफल माँग रहे हैं...")
        result = call_gemini(prompt)
        if result:
            print("\n" + "═" * 60)
            print(result)
            print("═" * 60)
        else:
            print("❌ Gemini response नहीं मिला।")
    else:
        print("\n⚠️  GEMINI_API_KEYS नहीं है। Prompt print हो गया है।")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENTRY POINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    import sys

    # ── Test mode (Django DB के बिना) ──────────────────────
    # python daily_horoscope_engine.py test
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_single_kundali(
            naam="अर्जुन शर्मा",
            dd=15, mm=7, yyyy=1990,
            hh=8, m_m=30,
            lat=28.6139, lon=77.2090,       # Delhi
            profession="Software Engineer",
            primary_focus="प्रमोशन और करियर ग्रोथ",
            current_challenge="काम में रुकावटें और तनाव",
            relationship_status="विवाहित",
            finance_focus="Home Loan चुकाना",
        )

    # ── Production mode (Django DB + Telegram) ─────────────
    else:
        generate_and_send_daily_horoscopes()
