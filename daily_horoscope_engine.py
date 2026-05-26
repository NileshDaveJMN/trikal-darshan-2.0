"""
================================================================
  त्रिकाल दर्शन - IMPROVED DAILY HOROSCOPE ENGINE v3.0
  (Vedic Moon-Sign Centric Update)
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
for i in range(1, 10):
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

RASHI_LORD = {
    0: "मंगल", 1: "शुक्र", 2: "बुध", 3: "चंद्र",
    4: "सूर्य", 5: "बुध", 6: "शुक्र", 7: "मंगल",
    8: "गुरु", 9: "शनि", 10: "शनि", 11: "गुरु"
}

UCCHA = {
    "सूर्य":  (0, 10), "चंद्र":  (1, 3), "मंगल":  (9, 28),
    "बुध":   (5, 15), "गुरु":  (3, 5), "शुक्र": (11, 27),
    "शनि":  (6, 20), "राहु":  (2, 20), "केतु":  (8, 20),
}

NEECHA_RASHI = {
    "सूर्य": 6, "चंद्र": 7, "मंगल": 3,
    "बुध": 11, "गुरु": 9, "शुक्र": 5,
    "शनि": 0, "राहु": 8, "केतु": 2
}

SWE_IDS = {
    "सूर्य":  swe.SUN, "चंद्र":  swe.MOON, "मंगल":  swe.MARS,
    "बुध":   swe.MERCURY, "गुरु":  swe.JUPITER, "शुक्र": swe.VENUS,
    "शनि":  swe.SATURN, "राहु":  swe.TRUE_NODE,
}

# Gochar rules: Favorable houses from Natal Moon
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
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    result, _ = swe.calc_ut(jd, planet_id, flags)
    tropical_lon = result[0]
    speed = result[3]
    ayan = _get_ayanamsha(jd)
    vedic = (tropical_lon - ayan) % 360
    return vedic, speed < 0

def _get_avastha(graha: str, rashi_idx: int, degree: float) -> str:
    if graha in UCCHA:
        u_rashi, u_deg = UCCHA[graha]
        if rashi_idx == u_rashi:
            if abs(degree - u_deg) <= 3:
                return "परम उच्च ✨"
            return "उच्च राशि 🌟"
    if graha in NEECHA_RASHI and rashi_idx == NEECHA_RASHI[graha]:
        return "नीच राशि ⚠️"
    swa = [r for r, lord in RASHI_LORD.items() if lord == graha]
    if rashi_idx in swa:
        return "स्व राशि 💪"
    return "सम 🔵"

def calculate_transit_positions(jd: float) -> dict:
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
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    ayan = _get_ayanamsha(jd)
    cusps, ascmc = swe.houses(jd, lat, lon, b'W')
    asc_sid = (ascmc[0] - ayan) % 360
    return int(asc_sid / 30)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SECTION 3 — VEDIC ANALYSIS (Gochar + Dasha + SAT)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def check_saadesati(natal_chandra_idx: int, transit_shani_idx: int) -> tuple[bool, str]:
    shani_from_chandra = (transit_shani_idx - natal_chandra_idx) % 12 + 1

    if shani_from_chandra == 12:
        return True, "⚠️ शनि साढ़ेसाती का पहला चरण (12वाँ भाव): खर्च और मानसिक तनाव हो सकता है। धैर्य रखें।"
    elif shani_from_chandra == 1:
        return True, "⚠️ शनि साढ़ेसाती का मुख्य चरण (1ला भाव): स्वास्थ्य और कार्य पर दबाव। शनि मंत्र जाप करें।"
    elif shani_from_chandra == 2:
        return True, "⚠️ शनि साढ़ेसाती का अंतिम चरण (2रा भाव): आर्थिक दबाव हो सकता है। मेहनत करते रहें।"
    elif shani_from_chandra == 4:
        return True, "🔶 कंटक शनि (4थे भाव से): गृह-जीवन में उथल-पुथल। परिवार में संयम रखें।"
    elif shani_from_chandra == 8:
        return True, "🔶 कंटक शनि (8वें भाव से): अचानक परेशानियाँ आ सकती हैं। वाहन-चालन में सावधानी बरतें।"
    return False, f"✅ शनि गोचर सामान्य है (चंद्र से {shani_from_chandra}वाँ स्थान)।"

def check_guru_gochar(natal_chandra_idx: int, transit_guru_idx: int) -> str:
    """गुरु का चंद्र राशि से गोचर विश्लेषण (वैदिक नियम)"""
    guru_from_chandra = (transit_guru_idx - natal_chandra_idx) % 12 + 1

    GURU_PHAL = {
        1: "⚠️ गुरु चंद्र राशि में — मानसिक चिंता और व्यय।",
        2: "💰 गुरु 2रे भाव में — धन प्राप्ति, पारिवारिक सुख और शुभ समाचार।",
        3: "⚠️ गुरु 3रे भाव में — स्थान परिवर्तन, कार्य में रुकावट।",
        4: "⚠️ गुरु 4थे भाव में — पारिवारिक उलझन, सुख में कमी।",
        5: "🎓 गुरु 5वें भाव में — शिक्षा, संतान सुख, और धन लाभ के लिए अत्यंत शुभ।",
        6: "⚠️ गुरु 6वें भाव में — रोग, शत्रु भय और चिंता।",
        7: "💑 गुरु 7वें भाव में — विवाह, साझेदारी और सम्मान प्राप्ति।",
        8: "⚠️ गुरु 8वें भाव में — अचानक परेशानियाँ, स्वास्थ्य कष्ट।",
        9: "🙏 गुरु 9वें भाव में — भाग्योदय! धर्म-कर्म और उन्नति का समय।",
        10: "⚠️ गुरु 10वें भाव में — कार्यक्षेत्र में बदलाव या अस्थिरता।",
        11: "🏆 गुरु 11वें भाव में — आय में वृद्धि, मनोकामनाएँ पूरी होने का उत्तम योग।",
        12: "⚠️ गुरु 12वें भाव में — अत्यधिक खर्च और दूर की यात्रा।",
    }
    return GURU_PHAL.get(guru_from_chandra, f"गुरु चंद्र राशि से {guru_from_chandra}वें भाव में है।")

def get_transit_ashtakvarg_score(natal_chandra_idx: int, transit_pos: dict) -> dict:
    """
    मुख्य ग्रहों का चंद्र राशि से गोचर स्कोर (शुभ/अशुभ)।
    """
    results = {}
    key_grahas = ["शनि", "गुरु", "मंगल", "सूर्य", "चंद्र", "बुध", "शुक्र"]

    for g in key_grahas:
        if g not in transit_pos:
            continue
        transit_r = transit_pos[g]["rashi_idx"]
        house_from_moon = (transit_r - natal_chandra_idx) % 12 + 1
        good_houses = TRANSIT_GOOD_HOUSES.get(g, [])
        is_good = house_from_moon in good_houses
        results[g] = {
            "house": house_from_moon,
            "score_label": "शुभ ✅" if is_good else "अशुभ ⚠️",
        }
    return results

def get_vakri_grahas(transit_pos: dict) -> list[str]:
    return [g for g, data in transit_pos.items() if data.get("vakri")]

def get_asta_grahas(transit_pos: dict) -> list[str]:
    """
    अस्त ग्रह: जो ग्रह सूर्य के बहुत निकट हों।
    Parashari नियम — सूर्य से अंशात्मक दूरी सीमाएँ:
      चंद्र: 12°, मंगल: 17°, बुध: 14° (vakri में 12°),
      गुरु: 11°, शुक्र: 10° (vakri में 8°), शनि: 15°
    राहु/केतु/सूर्य खुद अस्त नहीं होते।
    """
    ASTA_LIMITS = {
        "चंद्र": 12,
        "मंगल": 17,
        "बुध":  14,
        "गुरु": 11,
        "शुक्र": 10,
        "शनि": 15,
    }
    surya_lon = transit_pos["सूर्य"]["full_deg"]
    asta = []
    for graha, limit in ASTA_LIMITS.items():
        if graha not in transit_pos:
            continue
        graha_lon = transit_pos[graha]["full_deg"]
        diff = abs(surya_lon - graha_lon)
        if diff > 180:
            diff = 360 - diff
        if graha == "बुध" and transit_pos[graha].get("vakri"):
            limit = 12
        if graha == "शुक्र" and transit_pos[graha].get("vakri"):
            limit = 8
        if diff <= limit:
            asta.append(graha)
    return asta

def build_dasha_info(kundali) -> dict:
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
        moon_res, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
        moon_deg = moon_res[0]

        dasha_list, curr_dasha = get_vimshottari_dasha(moon_deg, dt_ist)

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
    asta_grahas: list[str],
) -> str:
    today_str = datetime.date.today().strftime("%d %B %Y")
    natal_chandra = natal_pos["चंद्र"]["rashi"]
    natal_chandra_nak = natal_pos["चंद्र"]["nakshatra"]
    natal_chandra_deg = natal_pos["चंद्र"]["degree"]
    natal_lagna = RASHI_NAMES[lagna_idx]

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

    key_transit = ["सूर्य", "चंद्र", "मंगल", "बुध", "गुरु", "शुक्र", "शनि", "राहु", "केतु"]
    transit_lines = []
    for g in key_transit:
        d = transit_pos[g]
        vakri_flag = " (वक्री 🔄)" if d["vakri"] else ""
        transit_lines.append(
            f"  {g}: {d['rashi']} {d['degree']:.1f}° | {d['nakshatra']} | {d['avastha']}{vakri_flag}"
        )
    transit_text = "\n".join(transit_lines)

    # ── Natal graha positions (lagna se bhav) ───────────────
    natal_lines = []
    for g in key_transit:
        if g not in natal_pos:
            continue
        d = natal_pos[g]
        bhav = (d["rashi_idx"] - lagna_idx) % 12 + 1
        vakri_flag = " (वक्री)" if d.get("vakri") else ""
        natal_lines.append(
            f"  {g}: {d['rashi']} {d['degree']:.1f}° | {d['nakshatra']} | {d['avastha']} | लग्न से {bhav}वाँ भाव{vakri_flag}"
        )
    natal_text = "\n".join(natal_lines)

    av_lines = [
        f"  {g}: जन्म चंद्र से {v['house']}वाँ भाव → {v['score_label']}"
        for g, v in ashtakvarg.items()
    ]
    av_text = "\n".join(av_lines)

    vakri_text = "、".join(vakri_grahas) if vakri_grahas else "कोई नहीं"
    asta_text  = "、".join(asta_grahas) if asta_grahas else "कोई नहीं"

    prompt = f"""
आज की तारीख: {today_str}

आप एक अनुभवी वैदिक ज्योतिषी हैं जो पाराशरी सिद्धांतों पर आधारित सटीक, प्रेरक और व्यक्तिगत फलित देते हैं।

══════════════════════════════════════════════
 जातक की जन्म-कुंडली का सारांश
══════════════════════════════════════════════
  नाम:           {user_name}
  जन्म लग्न:      {natal_lagna}
  जन्म चंद्र-राशि: {natal_chandra} ({natal_chandra_nak} नक्षत्र, {natal_chandra_deg:.1f}°)
  वर्तमान महादशा:  {dasha['md']} महादशा (समाप्ति: {dasha['md_end']})
  वर्तमान अंतर्दशा: {dasha['ad']} अंतर्दशा (समाप्ति: {dasha['ad_end']})

══════════════════════════════════════════════
 यूजर की व्यक्तिगत स्थिति और प्राथमिकताएँ
══════════════════════════════════════════════
{profile_text}

══════════════════════════════════════════════
 जन्म कुंडली — ग्रह स्थिति (Natal Positions)
══════════════════════════════════════════════
{natal_text}

══════════════════════════════════════════════
 आज का सटीक गोचर (SwissEph Lahiri Ayanamsha)
══════════════════════════════════════════════
{transit_text}

══════════════════════════════════════════════
 गोचर अष्टकवर्ग स्कोर (जन्म चंद्र-राशि से transit)
══════════════════════════════════════════════
{av_text}
  वक्री ग्रह आज: {vakri_text}

══════════════════════════════════════════════
 विशेष ग्रह-योग
══════════════════════════════════════════════
  शनि साढ़ेसाती/कंटक: {saadesati_text}
  गुरु गोचर (चंद्र से): {guru_text}

══════════════════════════════════════════════
 फलित नियम (इन्हें सख्ती से पालन करें)
══════════════════════════════════════════════
1. दशा स्वामी ({dasha['md']}) और अंतर्दशा स्वामी ({dasha['ad']}) के गुण-दोष को आज के गोचर से मिलाकर फलित दें।
2. शुभ ग्रहों का transit good house में हो तो उसे उजागर करें; अशुभ transit हो तो समाधान/उपाय भी बताएँ।
3. फलित का आधार केवल kundali और gochar हो — दशा, गोचर और जन्म कुंडली से prediction निकालें।
   यूज़र की profile (पेशा: '{profile.profession or 'सामान्य'}', चुनौती: '{profile.current_challenge or 'सामान्य'}') 
   सिर्फ भाषा को relatable बनाने के लिए use करें।
   उदाहरण: अगर 3रे भाव में बुध शुभ है तो बोलें "संवाद और यात्रा शुभ है" — 
   profession देखकर यह मत बोलें कि "आपको नए client मिलेंगे।"
   करियर / आर्थिक / स्वास्थ्य / रिश्ते — जो भाव आज सक्रिय हो उसी का फल दें।
4. वक्री ग्रह ({vakri_text}) के प्रभाव पर एक वाक्य जरूर लिखें।
4b. अस्त ग्रह ({asta_text}) सूर्य की किरणों में छुपे हैं — इनकी शक्ति क्षीण होती है।
    अगर कोई शुभ ग्रह अस्त हो तो उसके फल में कमी बताएँ और उपाय सुझाएँ।
5. भाषा: सरल, उत्साहवर्धक, सकारात्मक हिंदी। कोई ** या ## Markdown नहीं।
6. लंबाई: 5-6 लाइन (न बहुत छोटा, न बहुत लंबा)।
7. शुरुआत: '{user_name} जी,' से करें।
8. अंत में एक छोटा वैदिक उपाय (रंग / मंत्र / कर्म / दान) जरूर बताएँ।
   उपाय की प्राथमिकता इस क्रम में रखें:
   (1) सबसे पहले — आज के सबसे प्रभावशाली या कठिन गोचर ग्रह पर आधारित उपाय दें
       (जैसे अगर बुध अस्त है → बुध उपाय; गुरु 8वें में है → गुरु उपाय)
   (2) अगर गोचर में कोई विशेष स्थिति न हो → अंतर्दशा स्वामी ({dasha['ad']}) का उपाय दें
   (3) अंतिम विकल्प → महादशा स्वामी ({dasha['md']}) का उपाय दें
   ⚠️ उपाय हर रोज़ अलग होना चाहिए — एक ही मंत्र या कर्म बार-बार repeat मत करो।
   आज का गोचर देखकर fresh और specific upay दो।
9. टोन: एक अनुभवी और करुणामय गुरु जैसा — डराएँ नहीं, मार्गदर्शन करें।
10. जन्म चंद्र-राशि ({natal_chandra}) से आज के गोचर ग्रहों की स्थिति का विश्लेषण ज़रूर करें। चंद्र-राशि से कौन सा ग्रह किस भाव में है यह बताकर फलित दें — जैसे 'आपकी {natal_chandra} राशि के लिए आज...' इस तरह चंद्र-राशि का स्पष्ट उल्लेख करें।
11. ⚠️ अत्यंत महत्वपूर्ण — जन्म कुंडली के ग्रह और आज के गोचर ग्रह को कभी मिलाएं नहीं:
    - जब जन्म कुंडली के किसी ग्रह की बात करें तो स्पष्ट लिखें: "आपकी जन्म कुंडली में {natal_lagna} लग्न से Xवें भाव में स्थित [ग्रह]..."
    - जब आज के गोचर की बात करें तो स्पष्ट लिखें: "आज गोचर में [ग्रह] आपकी {natal_chandra} राशि से Xवें भाव में..."
    - दोनों को एक ही वाक्य में मिलाकर गलत भाव न बताएँ।
"""
    return prompt.strip()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SECTION 5 — GEMINI API CALL (Multi-key Rotation + Retry)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from typing import Optional

def call_gemini(prompt: str, max_retries: int = 3) -> Optional[str]:
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
            }
        }
        try:
            resp = requests.post(url, json=payload, timeout=30, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    candidate = candidates[0]
                    if candidate.get("finishReason") == "SAFETY":
                        print(f"  ⚠️  Safety filter triggered (attempt {attempt})")
                        continue
                    parts = candidate.get("content", {}).get("parts", [])
                    if parts:
                        text = parts[0].get("text", "").strip()
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
    if not BOT_TOKEN:
        print("  ⚠️  BOT_TOKEN नहीं है, Telegram skip।")
        return False

    safe_text = (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )

    max_length = 400
    if len(safe_text) > max_length:
        final_text = safe_text[:max_length] + "...\n\n"
        final_text += "✨ <b>पूरा राशिफल देखने के लिए त्रिकाल दर्शन पोर्टल पर लॉगिन करें:</b>\n"
        final_text += "🌐 <a href='https://trikal-darshan-2-0.onrender.com/'>यहाँ क्लिक करें</a>"
    else:
        final_text = safe_text

    header = "<b>🔮 त्रिकाल दर्शन — आपका आज का राशिफल</b>\n\n"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id":    chat_id,
        "text":       header + final_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
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
    user_name = profile.user.first_name or profile.user.username
    print(f"\n  👤 {user_name} ({profile.user.username})")

    kundali = (
        SavedKundali.objects
        .filter(user=profile.user)
        .order_by("created_at")
        .first()
    )
    if not kundali:
        print("     ⚠️  कोई SavedKundali नहीं मिली, skip।")
        return False

    natal_pos, natal_jd = calculate_natal_positions(kundali)
    lagna_idx = calculate_lagna(natal_jd, kundali.lat, kundali.lon)

    dasha = build_dasha_info(kundali)
    print(f"     📅 Dasha: {dasha['md']} / {dasha['ad']}")

    natal_chandra_idx = natal_pos["चंद्र"]["rashi_idx"]
    transit_shani_idx = today_transit["शनि"]["rashi_idx"]
    transit_guru_idx = today_transit["गुरु"]["rashi_idx"]

    saadesati_active, saadesati_text = check_saadesati(natal_chandra_idx, transit_shani_idx)
    guru_text = check_guru_gochar(natal_chandra_idx, transit_guru_idx)
    ashtakvarg = get_transit_ashtakvarg_score(natal_chandra_idx, today_transit)

    vakri = get_vakri_grahas(today_transit)
    asta  = get_asta_grahas(today_transit)

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
        asta_grahas=asta,
    )

    rashifal_text = call_gemini(prompt)
    if not rashifal_text:
        print("     ❌ Gemini से जवाब नहीं मिला।")
        return False

    print(f"     ✅ राशिफल बना: {len(rashifal_text)} characters")

    profile.daily_horoscope_text = rashifal_text
    profile.horoscope_date = datetime.date.today()
    profile.save(update_fields=["daily_horoscope_text", "horoscope_date"])

    if profile.telegram_chat_id:
        ok = send_telegram(profile.telegram_chat_id, rashifal_text)
        print(f"     📱 Telegram: {'✅ भेजा' if ok else '❌ विफल'}")
    else:
        print("     📱 Telegram: chat_id नहीं है, skip।")

    return True


def generate_and_send_daily_horoscopes():
    print("\n" + "━" * 60)
    print("  🔮 त्रिकाल दर्शन — Daily Horoscope Engine v3.0")
    print("━" * 60)
    print(f"  📅 आज: {datetime.date.today()}")

    if not GEMINI_API_KEYS:
        print("  ❌ GEMINI_API_KEYS नहीं मिलीं! .env चेक करें।")
        return

    tz = pytz.timezone("Asia/Kolkata")
    now = datetime.datetime.now(tz)
    today_jd = _dt_to_jd(now, "Asia/Kolkata")
    today_transit = calculate_transit_positions(today_jd)

    print("\n  🪐 आज का गोचर:")
    for g in ["सूर्य", "चंद्र", "मंगल", "बुध", "गुरु", "शुक्र", "शनि", "राहु"]:
        d = today_transit[g]
        vakri = " 🔄" if d["vakri"] else ""
        print(f"     {g:<6}: {d['rashi']} {d['degree']:.1f}° | {d['nakshatra']}{vakri} | {d['avastha']}")

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
        # if profile.horoscope_date == today:
        #   skipped += 1
        #   continue

        success = process_one_user(profile, today_transit, today_jd)
        if success:
            sent += 1
        else:
            failed += 1
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
    print(f"\n🧪 Test Mode: {naam} की कुंडली")

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

    tz = pytz.timezone("Asia/Kolkata")
    today_jd = _dt_to_jd(datetime.datetime.now(tz), "Asia/Kolkata")
    today_transit = calculate_transit_positions(today_jd)

    natal_pos, natal_jd = calculate_natal_positions(mock_kundali)
    lagna_idx = calculate_lagna(natal_jd, lat, lon)
    dasha = build_dasha_info(mock_kundali)

    natal_chandra_idx = natal_pos["चंद्र"]["rashi_idx"]
    _, saadesati_text = check_saadesati(natal_chandra_idx, today_transit["शनि"]["rashi_idx"])
    guru_text = check_guru_gochar(natal_chandra_idx, today_transit["गुरु"]["rashi_idx"])
    ashtakvarg = get_transit_ashtakvarg_score(natal_chandra_idx, today_transit)

    vakri = get_vakri_grahas(today_transit)
    asta  = get_asta_grahas(today_transit)

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
        asta_grahas=asta,
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

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_single_kundali(
            naam="अर्जुन शर्मा",
            dd=15, mm=7, yyyy=1990,
            hh=8, m_m=30,
            lat=28.6139, lon=77.2090,
            profession="Software Engineer",
            primary_focus="प्रमोशन और करियर ग्रोथ",
            current_challenge="काम में रुकावटें और तनाव",
            relationship_status="विवाहित",
            finance_focus="Home Loan चुकाना",
        )
    else:
        generate_and_send_daily_horoscopes()
