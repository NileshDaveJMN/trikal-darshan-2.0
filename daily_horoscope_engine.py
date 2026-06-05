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

# .env Auto-Load
_env_path = Path(__file__).parent / '.env'
if _env_path.exists():
    for _line in _env_path.read_text(encoding='utf-8').splitlines():
        _line = _line.strip()
        if _line and '=' in _line and not _line.startswith('#'):
            _k, _v = _line.split('=', 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# Django Setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trikal_portal.settings')
import django
django.setup()

# 🚀 नए मॉडल UserNotification को यहाँ इम्पोर्ट किया गया है
from core.models import UserProfile, SavedKundali, DailyRashifal, UserNotification
from core.views.rashifal_views import RASHI_LIST, _generate_rashifal, _get_transit_summary

from engines.kundali_engine import get_vimshottari_dasha
import swisseph as swe
import pytz

# API Keys Setup
GEMINI_API_KEYS = []
for i in range(1, 10):
    key = os.getenv(f"GEMINI_API_KEYS{i}", "").strip()
    if key:
        GEMINI_API_KEYS.append(key)
GEMINI_MODEL = "gemini-3-flash-preview"

# Vedic Constants
RASHI_NAMES = ["मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"]
NAKSHATRA_NAMES = ["अश्विनी", "भरणी", "कृत्तिका", "रोहिणी", "मृगशिरा", "आर्द्रा", "पुनर्वसु", "पुष्य", "आश्लेषा", "मघा", "पूर्वाफाल्गुनी", "उत्तराफाल्गुनी", "हस्त", "चित्रा", "स्वाती", "विशाखा", "अनुराधा", "ज्येष्ठा", "मूल", "पूर्वाषाढ़ा", "उत्तराषाढ़ा", "श्रवण", "धनिष्ठा", "शतभिषा", "पूर्वाभाद्रपद", "उत्तराभाद्रपद", "रेवती"]
RASHI_LORD = {0: "मंगल", 1: "शुक्र", 2: "बुध", 3: "चंद्र", 4: "सूर्य", 5: "बुध", 6: "शुक्र", 7: "मंगल", 8: "गुरु", 9: "शनि", 10: "शनि", 11: "गुरु"}
UCCHA = {"सूर्य": (0, 10), "चंद्र": (1, 3), "मंगल": (9, 28), "बुध": (5, 15), "गुरु": (3, 5), "शुक्र": (11, 27), "शनि": (6, 20), "राहु": (2, 20), "केतु": (8, 20)}
NEECHA_RASHI = {"सूर्य": 6, "चंद्र": 7, "मंगल": 3, "बुध": 11, "गुरु": 9, "शुक्र": 5, "शनि": 0, "राहु": 8, "केतु": 2}
SWE_IDS = {"सूर्य": swe.SUN, "चंद्र": swe.MOON, "मंगल": swe.MARS, "बुध": swe.MERCURY, "गुरु": swe.JUPITER, "शुक्र": swe.VENUS, "शनि": swe.SATURN, "राहु": swe.TRUE_NODE}
TRANSIT_GOOD_HOUSES = {"शनि": [3, 6, 11], "गुरु": [2, 5, 7, 9, 11], "मंगल": [3, 6, 11], "सूर्य": [3, 6, 10, 11], "चंद्र": [1, 3, 6, 7, 10, 11], "बुध": [2, 4, 6, 8, 10, 11], "शुक्र": [1, 2, 3, 4, 5, 8, 9, 11, 12]}

# Swiss Ephemeris Core Functions
def _dt_to_jd(dt: datetime.datetime, tz_str: str = "Asia/Kolkata") -> float:
    tz = pytz.timezone(tz_str)
    if dt.tzinfo is None:
        dt = tz.localize(dt)
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

# Gemini Prompt & API
def build_horoscope_prompt(user_name, profile, natal_pos, transit_pos, lagna_idx, dasha, saadesati_text, guru_text, ashtakvarg, vakri_grahas, asta_grahas):
    today_str = datetime.date.today().strftime("%d %B %Y")
    n_chandra, n_nak, n_deg = natal_pos["चंद्र"]["rashi"], natal_pos["चंद्र"]["nakshatra"], natal_pos["चंद्र"]["degree"]
    
    transit_lines = [f"  {g}: {d['rashi']} {d['degree']:.1f}° | {d['nakshatra']} | {d['avastha']}{' (वक्री)' if d['vakri'] else ''}" for g, d in transit_pos.items() if g in ["सूर्य", "चंद्र", "मंगल", "बुध", "गुरु", "शुक्र", "शनि", "राहु", "केतु"]]
    natal_lines = [f"  {g}: {d['rashi']} {d['degree']:.1f}° | लग्न से {(d['rashi_idx'] - lagna_idx) % 12 + 1}वाँ भाव" for g, d in natal_pos.items() if g in ["सूर्य", "चंद्र", "मंगल", "बुध", "गुरु", "शुक्र", "शनि"]]
    av_lines = [f"  {g}: जन्म चंद्र से {v['house']}वाँ भाव → {v['score_label']}" for g, v in ashtakvarg.items()]

    return f"""
आज की तारीख: {today_str}
आप एक अनुभवी वैदिक ज्योतिषी हैं जो पाराशरी सिद्धांतों पर आधारित सटीक और व्यक्तिगत फलित देते हैं।

जन्म-कुंडली विवरण:
  नाम: {user_name}
  जन्म लग्न: {RASHI_NAMES[lagna_idx]}
  जन्म चंद्र-राशि: {n_chandra} ({n_nak} नक्षत्र, {n_deg:.1f}°)
  वर्तमान दशा: {dasha['md']} महादशा (अंत: {dasha['md_end']}) - {dasha['ad']} अंतर्दशा (अंत: {dasha['ad_end']})
  पेशा: {profile.profession or 'सामान्य'} | फोकस: {profile.primary_focus or 'सामान्य'}

जन्म कुंडली ग्रह:
{chr(10).join(natal_lines)}

आज का गोचर:
{chr(10).join(transit_lines)}

गोचर अष्टकवर्ग (चंद्र से):
{chr(10).join(av_lines)}
  वक्री: {'、'.join(vakri_grahas) if vakri_grahas else 'कोई नहीं'} | अस्त: {'、'.join(asta_grahas) if asta_grahas else 'कोई नहीं'}
  शनि गोचर: {saadesati_text}
  गुरु गोचर: {guru_text}

नियम:
1. सरल, सकारात्मक हिंदी में 5-6 लाइन का राशिफल दें।
2. शुरुआत '{user_name} जी,' से करें।
3. जन्म चंद्र-राशि ({n_chandra}) के अनुसार आज के गोचर का फल दें।
4. दशा स्वामी और गोचर को मिलाकर फलित निकालें।
5. अंत में आज के गोचर के अनुसार एक छोटा, स्पष्ट वैदिक उपाय जरूर बताएँ।
"""

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

def pre_generate_12_rashifal():
    print("\n  🌟 जनरेटिंग 12 राशियों का सामान्य राशिफल (Pre-caching)...")
    today = datetime.date.today()
    transit_text = _get_transit_summary()

    for rashi in RASHI_LIST:
        if DailyRashifal.objects.filter(date=today, rashi_id=rashi["id"]).exists():
            print(f"     ✅ {rashi['name']} - पहले से डेटाबेस में मौजूद है।")
            continue

        print(f"     ⏳ {rashi['name']} राशि जनरेट हो रही है...")
        data = _generate_rashifal(rashi["name"], rashi["lord"], transit_text)
        
        if data:
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
            print(f"     ✅ {rashi['name']} सफलतापूर्वक सेव हो गया।")
        else:
            print(f"     ❌ {rashi['name']} फेल हो गया!")
            
        time.sleep(2)

def process_one_user(profile: UserProfile, today_transit: dict, today_jd: float) -> bool:
    user_name = profile.user.first_name or profile.user.username
    print(f"\n  👤 {user_name} ({profile.user.username})")

    kundali = SavedKundali.objects.filter(user=profile.user).order_by("created_at").first()
    if not kundali:
        print("     ⚠️  कोई SavedKundali नहीं मिली, skip।")
        return False

    natal_pos, natal_jd = calculate_natal_positions(kundali)
    lagna_idx = calculate_lagna(natal_jd, kundali.lat, kundali.lon)
    dasha = build_dasha_info(kundali)
    
    n_chandra_idx = natal_pos["चंद्र"]["rashi_idx"]
    _, saadesati_text = check_saadesati(n_chandra_idx, today_transit["शनि"]["rashi_idx"])
    
    prompt = build_horoscope_prompt(
        user_name, profile, natal_pos, today_transit, lagna_idx, dasha,
        saadesati_text, check_guru_gochar(n_chandra_idx, today_transit["गुरु"]["rashi_idx"]),
        get_transit_ashtakvarg_score(n_chandra_idx, today_transit),
        get_vakri_grahas(today_transit), get_asta_grahas(today_transit)
    )

    rashifal_text = call_gemini(prompt)
    if not rashifal_text:
        print("     ❌ Gemini से जवाब नहीं मिला।")
        return False

    # 🚀 यहाँ से हमने नया UserNotification सेव करने का लॉजिक जोड़ दिया है
    today_str = datetime.date.today().strftime("%d %b %Y")
    UserNotification.objects.create(
        user=profile.user,
        title=f"🔮 आज का राशिफल ({today_str})",
        message=rashifal_text,
        notification_type='DAILY'
    )
    
    print("     ✅ राशिफल नए Notification इनबॉक्स में सफलतापूर्वक सेव हो गया।")
    return True

def generate_daily_horoscopes():
    print("\n" + "━" * 60)
    print("  🔮 त्रिकाल दर्शन — Daily Horoscope Engine v3.2 (Inbox Ready)")
    print("━" * 60)

    if not GEMINI_API_KEYS:
        print("  ❌ GEMINI_API_KEYS नहीं मिलीं! .env चेक करें।")
        return

    pre_generate_12_rashifal()

    print("\n  🚀 अब यूज़र्स का व्यक्तिगत राशिफल जनरेट हो रहा है...")
    today_jd = _dt_to_jd(datetime.datetime.now(pytz.timezone("Asia/Kolkata")), "Asia/Kolkata")
    today_transit = calculate_transit_positions(today_jd)

    profiles = UserProfile.objects.select_related("user").all()
    print(f"\n  👥 कुल Users: {profiles.count()}")

    sent, failed = 0, 0
    for profile in profiles:
        if process_one_user(profile, today_transit, today_jd): sent += 1
        else: failed += 1
        time.sleep(0.5)

    print("\n" + "━" * 60)
    print(f"  ✅ पर्सनल राशिफल जनरेट हुए: {sent} | ❌ विफल: {failed}")
    print("━" * 60 + "\n")

if __name__ == "__main__":
    generate_daily_horoscopes()
