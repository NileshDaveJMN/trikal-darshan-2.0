import os
import sys
import datetime
import random
import re
import time
import requests
import urllib3
import swisseph as swe
import pytz

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from core.models import UserProfile, SavedKundali, DailyRashifal, UserNotification
# ✏️ UPDATED: _generate_rashifal / _get_transit_summary ke imports hataye —
#            wo rashifal_views ke buggy functions the (silent exception + 5.5h IST/UT offset).
#            Ab engine apna sahi calculation use karta hai.
from core.views.rashifal_views import RASHI_LIST
from engines.kundali_engine import get_vimshottari_dasha

# API Keys Setup
GEMINI_API_KEYS = []
for i in range(1, 10):
    key = os.getenv(f"GEMINI_API_KEYS{i}", "").strip()
    if key: GEMINI_API_KEYS.append(key)
GEMINI_MODEL = "gemini-3-flash-preview"

# Vedic Constants
RASHI_NAMES = ["मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"]
NAKSHATRA_NAMES = ["अश्विनी", "भरणी", "कृत्तिका", "रोहिणी", "मृगशिरा", "आर्द्रा", "पुनर्वसु", "पुष्य", "आश्लेषा", "मघा", "पूर्वाफाल्गुनी", "उत्तराफाल्गुनी", "हस्त", "चित्रा", "स्वाति", "विशाखा", "अनुराधा", "ज्येष्ठा", "मूल", "पूर्वाषाढ़ा", "उत्तराषाढ़ा", "श्रवण", "धनिष्ठा", "शतभिषा", "पूर्वाभाद्रपद", "उत्तराभाद्रपद", "रेवती"]
RASHI_LORD = {0: "मंगल", 1: "शुक्र", 2: "बुध", 3: "चंद्र", 4: "सूर्य", 5: "बुध", 6: "शुक्र", 7: "मंगल", 8: "गुरु", 9: "शनि", 10: "शनि", 11: "गुरु"}
UCCHA = {"सूर्य": (0, 10), "चंद्र": (1, 3), "मंगल": (9, 28), "बुध": (5, 15), "गुरु": (3, 5), "शुक्र": (11, 27), "शनि": (6, 20), "राहु": (2, 20), "केतु": (8, 20)}
NEECHA_RASHI = {"सूर्य": 6, "चंद्र": 7, "मंगल": 3, "बुध": 11, "गुरु": 9, "शुक्र": 5, "शनि": 0, "राहु": 8, "केतु": 2}
SWE_IDS = {"सूर्य": swe.SUN, "चंद्र": swe.MOON, "मंगल": swe.MARS, "बुध": swe.MERCURY, "गुरु": swe.JUPITER, "शुक्र": swe.VENUS, "शनि": swe.SATURN, "राहु": swe.TRUE_NODE}
TRANSIT_GOOD_HOUSES = {"शनि": [3, 6, 11], "गुरु": [2, 5, 7, 9, 11], "मंगल": [3, 6, 11], "सूर्य": [3, 6, 10, 11], "चंद्र": [1, 3, 6, 7, 10, 11], "बुध": [2, 4, 6, 8, 10, 11], "शुक्र": [1, 2, 3, 4, 5, 8, 9, 11, 12]}

# ═══════════════════════════════════════════════════════════════════
# 🆕 NEW: Daily-changing anchors — vaar, tithi, nakshatra-swami
# Ye roz badalte hain → prompt ka mudda (focus) aur upay roz alag banega
# ═══════════════════════════════════════════════════════════════════
VAAR_HI = ["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"]   # weekday(): Mon=0
TITHI_HI = ["प्रतिपदा", "द्वितीया", "तृतीया", "चतुर्थी", "पंचमी", "षष्ठी", "सप्तमी", "अष्टमी",
            "नवमी", "दशमी", "एकादशी", "द्वादशी", "त्रयोदशी", "चतुर्दशी"]                # 15vaan = पूर्णिमा/अमावस्या
VAAR_THEME = {
    "सोमवार": "मन और भावनाएँ", "मंगलवार": "साहस और कार्य-ऊर्जा", "बुधवार": "संचार और व्यापार",
    "गुरुवार": "ज्ञान और भाग्य", "शुक्रवार": "संबंध और सुख", "शनिवार": "धैर्य और कर्तव्य",
    "रविवार": "आत्मविश्वास और स्वास्थ्य",
}
NAKSHATRA_LORD = {
    "अश्विनी": "केतु", "भरणी": "शुक्र", "कृत्तिका": "सूर्य", "रोहिणी": "चंद्र",
    "मृगशिरा": "मंगल", "आर्द्रा": "राहु", "पुनर्वसु": "गुरु", "पुष्य": "शनि",
    "आश्लेषा": "बुध", "मघा": "केतु", "पूर्वाफाल्गुनी": "शुक्र", "उत्तराफाल्गुनी": "सूर्य",
    "हस्त": "चंद्र", "चित्रा": "मंगल", "स्वाति": "राहु", "विशाखा": "गुरु",
    "अनुराधा": "शनि", "ज्येष्ठा": "बुध", "मूल": "केतु", "पूर्वाषाढ़ा": "शुक्र",
    "उत्तराषाढ़ा": "सूर्य", "श्रवण": "चंद्र", "धनिष्ठा": "मंगल", "शतभिषा": "राहु",
    "पूर्वाभाद्रपद": "गुरु", "उत्तराभाद्रपद": "शनि", "रेवती": "बुध",
}

def _get_tithi(transit_pos):
    """🆕 Transit Moon-Sun se aaj ki tithi — roz badalti hai"""
    moon, sun = transit_pos["चंद्र"], transit_pos["सूर्य"]
    elong = (moon["full_deg"] - sun["full_deg"]) % 360
    t_num = int(elong // 12) + 1                     # 1..30
    paksha = "शुक्ल" if t_num <= 15 else "कृष्ण"
    t_pos = t_num if t_num <= 15 else t_num - 15     # 1..15
    tithi = ("पूर्णिमा" if paksha == "शुक्ल" else "अमावस्या") if t_pos == 15 else TITHI_HI[t_pos - 1]
    return paksha, tithi

# Swiss Ephemeris Core Functions
def _dt_to_jd(dt: datetime.datetime, tz_str: str = "Asia/Kolkata") -> float:
    tz = pytz.timezone(tz_str)
    if dt.tzinfo is None: dt = tz.localize(dt)
    dt_utc = dt.astimezone(pytz.utc)
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0)

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
            return "परम उच्च ✨" if abs(degree - u_deg) <= 3 else "उच्च राशि 🌟"
    if graha in NEECHA_RASHI and rashi_idx == NEECHA_RASHI[graha]:
        return "नीच राशि ⚠️"
    swa = [r for r, lord in RASHI_LORD.items() if lord == graha]
    return "स्व राशि 💪" if rashi_idx in swa else "सम 🔵"

def calculate_transit_positions(jd: float) -> dict:
    positions = {}
    for naam, pid in SWE_IDS.items():
        lon, retro = _vedic_lon(pid, jd)
        r_idx = int(lon / 30)
        deg_in_r = lon % 30
        positions[naam] = {
            "rashi": RASHI_NAMES[r_idx], "rashi_idx": r_idx, "degree": round(deg_in_r, 2),
            "full_deg": round(lon, 4), "nakshatra": NAKSHATRA_NAMES[int(lon / (360 / 27))],
            "vakri": retro, "avastha": _get_avastha(naam, r_idx, deg_in_r)
        }
    rahu_lon = positions["राहु"]["full_deg"]
    ketu_lon = (rahu_lon + 180) % 360
    k_idx = int(ketu_lon / 30)
    positions["केतु"] = {
        "rashi": RASHI_NAMES[k_idx], "rashi_idx": k_idx, "degree": round(ketu_lon % 30, 2),
        "full_deg": round(ketu_lon, 4), "nakshatra": NAKSHATRA_NAMES[int(ketu_lon / (360 / 27))],
        "vakri": True, "avastha": _get_avastha("केतु", k_idx, ketu_lon % 30)
    }
    return positions

def calculate_natal_positions(kundali) -> dict:
    dt_ist = datetime.datetime(kundali.year, kundali.month, kundali.day, kundali.hour, kundali.minute, kundali.second)
    dt_utc = dt_ist - datetime.timedelta(hours=5, minutes=30)
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0)
    return calculate_transit_positions(jd), jd

def calculate_lagna(jd: float, lat: float, lon: float) -> int:
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    ayan = _get_ayanamsha(jd)
    cusps, ascmc = swe.houses(jd, lat, lon, b'W')
    return int(((ascmc[0] - ayan) % 360) / 30)

# Vedic Analysis Functions
def check_saadesati(natal_chandra_idx: int, transit_shani_idx: int) -> tuple[bool, str]:
    shani_from_chandra = (transit_shani_idx - natal_chandra_idx) % 12 + 1
    if shani_from_chandra == 12: return True, "⚠️ शनि साढ़ेसाती का पहला चरण (12वाँ भाव): खर्च और मानसिक तनाव हो सकता है। धैर्य रखें।"
    if shani_from_chandra == 1: return True, "⚠️ शनि साढ़ेसाती का मुख्य चरण (1ला भाव): स्वास्थ्य और कार्य पर दबाव। शनि मंत्र जाप करें।"
    if shani_from_chandra == 2: return True, "⚠️ शनि साढ़ेसाती का अंतिम चरण (2रा भाव): आर्थिक दबाव हो सकता है। मेहनत करते रहें।"
    if shani_from_chandra == 4: return True, "🔶 कंटक शनि (4थे भाव से): गृह-जीवन में उथल-पुथल। परिवार में संयम रखें।"
    if shani_from_chandra == 8: return True, "🔶 कंटक शनि (8वें भाव से): अचानक परेशानियाँ आ सकती हैं। सावधानी बरतें।"
    return False, f"✅ शनि गोचर सामान्य है (चंद्र से {shani_from_chandra}वाँ स्थान)।"

def check_guru_gochar(natal_chandra_idx: int, transit_guru_idx: int) -> str:
    guru_from_chandra = (transit_guru_idx - natal_chandra_idx) % 12 + 1
    GURU_PHAL = {
        1: "⚠️ मानसिक चिंता और व्यय।", 2: "💰 धन प्राप्ति, पारिवारिक सुख।", 3: "⚠️ स्थान परिवर्तन, कार्य में रुकावट।",
        4: "⚠️ पारिवारिक उलझन।", 5: "🎓 शिक्षा और धन लाभ के लिए शुभ।", 6: "⚠️ रोग, शत्रु भय और चिंता।",
        7: "💑 साझेदारी और सम्मान प्राप्ति।", 8: "⚠️ अचानक परेशानियाँ।", 9: "🙏 भाग्योदय! उन्नति का समय।",
        10: "⚠️ कार्यक्षेत्र में बदलाव।", 11: "🏆 आय में वृद्धि, उत्तम योग।", 12: "⚠️ अत्यधिक खर्च और यात्रा।"
    }
    return GURU_PHAL.get(guru_from_chandra, f"गुरु चंद्र से {guru_from_chandra}वें भाव में है।")

def get_transit_ashtakvarg_score(natal_chandra_idx: int, transit_pos: dict) -> dict:
    results = {}
    for g in ["शनि", "गुरु", "मंगल", "सूर्य", "चंद्र", "बुध", "शुक्र"]:
        if g in transit_pos:
            house = (transit_pos[g]["rashi_idx"] - natal_chandra_idx) % 12 + 1
            results[g] = {"house": house, "score_label": "शुभ ✅" if house in TRANSIT_GOOD_HOUSES.get(g, []) else "अशुभ ⚠️"}
    return results

def get_vakri_grahas(transit_pos: dict) -> list[str]:
    return [g for g, data in transit_pos.items() if data.get("vakri")]

def get_asta_grahas(transit_pos: dict) -> list[str]:
    ASTA_LIMITS = {"चंद्र": 12, "मंगल": 17, "बुध": 14, "गुरु": 11, "शुक्र": 10, "शनि": 15}
    surya_lon = transit_pos["सूर्य"]["full_deg"]
    asta = []
    for graha, limit in ASTA_LIMITS.items():
        if graha not in transit_pos: continue
        diff = abs(surya_lon - transit_pos[graha]["full_deg"])
        diff = 360 - diff if diff > 180 else diff
        if graha == "बुध" and transit_pos[graha].get("vakri"): limit = 12
        if graha == "शुक्र" and transit_pos[graha].get("vakri"): limit = 8
        if diff <= limit: asta.append(graha)
    return asta

def build_dasha_info(kundali) -> dict:
    try:
        dt_ist = datetime.datetime(kundali.year, kundali.month, kundali.day, kundali.hour, kundali.minute, kundali.second)
        dt_utc = dt_ist - datetime.timedelta(hours=5, minutes=30)
        jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0)
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        moon_deg = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)[0][0]
        dasha_list, curr_dasha = get_vimshottari_dasha(moon_deg, dt_ist)

        md_end, ad_end = "अज्ञात", "अज्ञात"
        for md in dasha_list:
            if md["is_current"]:
                md_end = md["end"]
                for ad in md["antardashas"]:
                    if ad["is_current"]: ad_end = ad["end"]; break
                break
        return {"md": curr_dasha.get("md", "अज्ञात"), "ad": curr_dasha.get("ad", "अज्ञात"), "md_end": md_end, "ad_end": ad_end}
    except Exception as e:
        return {"md": "अज्ञात", "ad": "अज्ञात", "md_end": "-", "ad_end": "-"}

def call_gemini(prompt: str, max_retries: int = 3):
    if not GEMINI_API_KEYS: return None
    keys = GEMINI_API_KEYS.copy()
    random.shuffle(keys)
    for attempt, api_key in enumerate(keys[:max_retries], 1):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}"
        try:
            resp = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.75}}, timeout=30, verify=False)
            if resp.status_code == 200:
                text = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                return re.sub(r'[*#]', '', text) if text else None
            elif resp.status_code == 429: time.sleep(2)
        except Exception: time.sleep(1)
    return None

# ✏️ UPDATED: daily anchors (vaar/tithi/nakshatra-swami) + anti-repetition + naye rules
def build_horoscope_prompt(user_name, profile, natal_pos, transit_pos, lagna_idx, dasha,
                           saadesati_text, guru_text, ashtakvarg, vakri_grahas, asta_grahas,
                           yesterday_upay=""):
    # IST se date/vaar — UTC date bug bhi fix (00:00–05:30 IST mein galat date aati thi)
    IST = pytz.timezone("Asia/Kolkata")
    now = datetime.datetime.now(IST)
    today_str = now.strftime("%d %B %Y")
    vaar = VAAR_HI[now.weekday()]

    n_chandra, n_nak, n_deg = natal_pos["चंद्र"]["rashi"], natal_pos["चंद्र"]["nakshatra"], natal_pos["चंद्र"]["degree"]

    # 🆕 Aaj ki tithi aur transit chandra ka nakshatra + swami
    paksha, tithi = _get_tithi(transit_pos)
    moon = transit_pos["चंद्र"]
    t_nak = moon["nakshatra"]
    nak_lord = NAKSHATRA_LORD.get(t_nak, "चंद्र")

    transit_lines = [f"  {g}: {d['rashi']} {d['degree']:.1f}° | {d['nakshatra']} | {d['avastha']}{' (वक्री)' if d['vakri'] else ''}" for g, d in transit_pos.items() if g in ["सूर्य", "चंद्र", "मंगल", "बुध", "गुरु", "शुक्र", "शनि", "राहु", "केतु"]]
    natal_lines = [f"  {g}: {d['rashi']} {d['degree']:.1f}° | लग्न से {(d['rashi_idx'] - lagna_idx) % 12 + 1}वाँ भाव" for g, d in natal_pos.items() if g in ["सूर्य", "चंद्र", "मंगल", "बुध", "गुरु", "शुक्र", "शनि"]]
    av_lines = [f"  {g}: जन्म चंद्र से {v['house']}वाँ भाव → {v['score_label']}" for g, v in ashtakvarg.items()]

    # 🆕 Anti-repetition rule — sirf tab jab kal ka upay available ho
    upay_repeat_rule = ""
    if yesterday_upay:
        upay_repeat_rule = f"6. कल का उपाय यह था: \"{yesterday_upay}\" — आज इसे या इससे मिलता-जुलता उपाय बिल्कुल न दोहराएँ।\n"

    return f"""
आज की तारीख: {today_str} ({vaar})
तिथि: {paksha} {tithi} | चंद्र नक्षत्र: {t_nak} (स्वामी: {nak_lord}) | आज का केंद्रीय विषय: {VAAR_THEME[vaar]}

आप एक अनुभवी वैदिक ज्योतिषी हैं जो पाराशरी सिद्धांतों पर आधारित सटीक और व्यक्तिगत फलित देते हैं।

जन्म-कुंडली विवरण (केवल संदर्भ):
  नाम: {user_name}
  जन्म लग्न: {RASHI_NAMES[lagna_idx]}
  जन्म चंद्र-राशि: {n_chandra} ({n_nak} नक्षत्र, {n_deg:.1f}°)
  वर्तमान दशा: {dasha['md']} महादशा (अंत: {dasha['md_end']}) - {dasha['ad']} अंतर्दशा (अंत: {dasha['ad_end']})
  पेशा: {profile.profession or 'सामान्य'} | फोकस: {profile.primary_focus or 'सामान्य'}

जन्म कुंडली ग्रह (केवल संदर्भ):
{chr(10).join(natal_lines)}

आज का गोचर:
{chr(10).join(transit_lines)}

गोचर अष्टकवर्ग (चंद्र से):
{chr(10).join(av_lines)}
  वक्री: {', '.join(vakri_grahas) if vakri_grahas else 'कोई नहीं'} | अस्त: {', '.join(asta_grahas) if asta_grahas else 'कोई नहीं'}
  शनि गोचर: {saadesati_text}
  गुरु गोचर: {guru_text}

नियम:
1. सरल, सकारात्मक हिंदी में 5-6 लाइन का राशिफल दें। शुरुआत '{user_name} जी,' से करें।
2. राशिफल का मुख्य आधार आज का चंद्र-गोचर, नक्षत्र ({t_nak}), तिथि ({paksha} {tithi}) और वार ({vaar}) हो — ये रोज़ बदलते हैं। जन्म चंद्र-राशि ({n_chandra}) से गोचर के भाव गिनें।
3. दशा, गुरु गोचर, साढ़ेसाती और जन्म-कुंडली केवल संदर्भ हैं — इन पर राशिफल का भार न डालें (ये महीनों-वर्षों तक एक जैसे रहते हैं, रोज़ दोहराने योग्य नहीं)।
4. उपाय (सबसे ज़रूरी नियम): उपाय आज के चंद्र-नक्षत्र के स्वामी ग्रह ({nak_lord}), तिथि और वार पर आधारित हो। दशा या गुरु-गोचर पर आधारित उपाय बिल्कुल न दें।
5. अंत में "आज का विशेष उपाय:" लिखकर एक छोटा, स्पष्ट वैदिक उपाय जरूर बताएँ।
{upay_repeat_rule}"""

def _get_yesterday_upay(user):
    """🆕 Kal (ya sabse recent) DAILY rashifal se upay nikaalta hai — anti-repetition ke liye"""
    try:
        n = UserNotification.objects.filter(user=user, notification_type='DAILY') \
              .order_by('-created_at').first()
        if n and n.message:
            m = re.search(r"विशेष उपाय\s*[:\-]\s*(.+)", n.message, re.DOTALL) or \
                re.search(r"उपाय\s*[:\-]\s*(.+)", n.message, re.DOTALL)
            if m:
                return m.group(1).strip()[:250]
    except Exception:
        pass
    return ""

# ✏️ UPDATED: engine ka apna sahi transit + house-wise gochar (rashifal_views ke buggy
#            _get_transit_summary/_generate_rashifal pe depend karna hata diya) + IST date
def pre_generate_12_rashifal():
    print("\n  🌟 जनरेटिंग 12 राशियों का सामान्य राशिफल (Pre-caching)...")
    IST = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.datetime.now(IST)
    today = now_ist.date()
    vaar = VAAR_HI[now_ist.weekday()]
    transit = calculate_transit_positions(_dt_to_jd(now_ist))

    paksha, tithi = _get_tithi(transit)
    moon = transit["चंद्र"]
    nak_lord = NAKSHATRA_LORD.get(moon["nakshatra"], "चंद्र")

    for rashi in RASHI_LIST:
        if DailyRashifal.objects.filter(date=today, rashi_id=rashi["id"]).exists():
            continue
        print(f"     ⏳ {rashi['name']} राशि जनरेट हो रही है...")

        # 🆕 Har rashi ke liye house-wise gochar (us rashi se bhav ginkar)
        r_idx = rashi["idx"]
        gochar_lines = []
        for g, d in transit.items():
            house = (d["rashi_idx"] - r_idx) % 12 + 1
            line = f"  {g}: {d['rashi']} ({d['degree']:.1f}°) — इस राशि से भाव {house}"
            if d.get("vakri"):
                line += " (वक्री)"
            gochar_lines.append(line)

        prompt = f"""आज की तारीख: {today.strftime('%d %B %Y')} ({vaar})
आप एक अनुभवी वैदिक ज्योतिषी हैं। {rashi['name']} राशि (स्वामी: {rashi['lord']}) का आज का राशिफल लिखें।

आज का गोचर — इस राशि से भावों के हिसाब से:
{chr(10).join(gochar_lines)}
चंद्र नक्षत्र: {moon['nakshatra']} (स्वामी: {nak_lord}) | तिथि: {paksha} {tithi}

नीचे दिए गए विषयों पर 2-3 वाक्यों में सकारात्मक और व्यावहारिक मार्गदर्शन दें:
[GENERAL] सामान्य दिन कैसा रहेगा
[CAREER] करियर और व्यापार
[LOVE] प्रेम और रिश्ते
[HEALTH] स्वास्थ्य
[LUCKY] शुभ रंग, अंक और समय
[UPAY] आज का एक सरल उपाय

नियम:
- केवल हिंदी में लिखें, कोई Markdown (**, ##) न हो
- गोचर को आधार बनाएं: कौन-सा ग्रह इस राशि से किस भाव में है, उसका फल बताएं
- चंद्र की नक्षत्र और तिथि का प्रभाव शामिल करें
- उपाय चंद्र-नक्षत्र के स्वामी या वार के अनुसार हो
- हर विषय [TAG] से शुरू करें
"""
        raw = call_gemini(prompt)
        if raw:
            data = {}
            for tag in ["GENERAL", "CAREER", "LOVE", "HEALTH", "LUCKY", "UPAY"]:
                m = re.search(rf"\[{tag}\][:\s]*(.*?)(?=\[|$)", raw, re.DOTALL)
                data[tag] = m.group(1).strip() if m else ""
            DailyRashifal.objects.create(
                date=today,
                rashi_id=rashi["id"],
                general=data.get("GENERAL", ""),
                career=data.get("CAREER", ""),
                love=data.get("LOVE", ""),
                health=data.get("HEALTH", ""),
                lucky=data.get("LUCKY", ""),
                upay=data.get("UPAY", "")
            )
            print(f"     ✅ {rashi['name']} सेव हुई।")
        else:
            print(f"     ❌ {rashi['name']}: Gemini जवाब नहीं दिया।")
        time.sleep(2)

# 🚀 MASTER ENGINE द्वारा कॉल किया जाने वाला फंक्शन
# ✏️ UPDATED: IST date + yesterday_upay anti-repetition pass hota hai
def process_user_horoscope(profile, kundali, natal_pos, lagna_idx, dasha, today_transit):
    user_name = profile.user.first_name or profile.user.username
    IST = pytz.timezone("Asia/Kolkata")
    today_str = datetime.datetime.now(IST).strftime("%d %b %Y")

    # चेक करें कि क्या आज का राशिफल पहले से सेव्ड है
    if UserNotification.objects.filter(user=profile.user, title=f"🔮 आज का राशिफल ({today_str})", notification_type='DAILY').exists():
        print(f"     ℹ️  {user_name}: आज का व्यक्तिगत राशिफल पहले से मौजूद है। (Skip)")
        return False

    n_chandra_idx = natal_pos["चंद्र"]["rashi_idx"]
    _, saadesati_text = check_saadesati(n_chandra_idx, today_transit["शनि"]["rashi_idx"])
    guru_text = check_guru_gochar(n_chandra_idx, today_transit["गुरु"]["rashi_idx"])
    ashtakvarg = get_transit_ashtakvarg_score(n_chandra_idx, today_transit)
    vakri_grahas = get_vakri_grahas(today_transit)
    asta_grahas = get_asta_grahas(today_transit)

    prompt = build_horoscope_prompt(
        user_name, profile, natal_pos, today_transit, lagna_idx, dasha,
        saadesati_text, guru_text, ashtakvarg, vakri_grahas, asta_grahas,
        yesterday_upay=_get_yesterday_upay(profile.user)   # 🆕 anti-repetition
    )

    rashifal_text = call_gemini(prompt)
    if not rashifal_text:
        print(f"     ❌ {user_name}: Gemini से जवाब नहीं मिला।")
        return False

    UserNotification.objects.create(
        user=profile.user,
        title=f"🔮 आज का राशिफल ({today_str})",
        message=rashifal_text,
        notification_type='DAILY'
    )
    print(f"     ✅ {user_name}: व्यक्तिगत राशिफल इनबॉक्स में सेव हुआ।")
    return True