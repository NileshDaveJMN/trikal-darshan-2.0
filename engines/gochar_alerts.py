# engines/gochar_alerts.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# गोचर परिवर्तन अलर्ट इंजन
# जब कोई मुख्य ग्रह रashi बदले, तो यूज़र को व्यक्तिगत AI अलर्ट भेजे
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import os
import re
import random
import datetime
import time
import requests
import urllib3
import swisseph as swe
import pytz

from core.models import UserNotification

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Gemini API Setup ──────────────────────────────────────────────────
GEMINI_API_KEYS = []
for _i in range(1, 10):
    _k = os.environ.get(f"GEMINI_API_KEYS{_i}", "").strip()
    if _k:
        GEMINI_API_KEYS.append(_k)
GEMINI_MODEL = "gemini-2.0-flash-exp"

# ── Vedic Constants ───────────────────────────────────────────────────
RASHI_NAMES = ["मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या",
               "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"]

# सिर्फ इन मुख्य ग्रहों का गोचर महत्वपूर्ण माना जाता है
MAIN_GOCHAR_PLANETS = {
    "शनि":  swe.SATURN,    # ~2.5 साल एक रashi में
    "गुरु": swe.JUPITER,   # ~1 साल एक रashi में
    "राहु": swe.TRUE_NODE, # ~1.5 साल एक रashi में (केतु automatic)
    "मंगल": swe.MARS,      # ~45 दिन
    "सूर्य": swe.SUN,      # ~30 दिन (संक्रांति)
    "शुक्र": swe.VENUS,    # ~25 दिन (normal)
    "बुध":  swe.MERCURY,   # ~20 दिन
}

# ग्रह का महत्व और emoji
PLANET_INFO = {
    "शनि":  {"emoji": "🪐", "importance": "high",   "desc": "शनि का गोचर"},
    "गुरु": {"emoji": "🌟", "importance": "high",   "desc": "गुरु का गोचर"},
    "राहु": {"emoji": "🌑", "importance": "high",   "desc": "राहु-केतु का गोचर"},
    "मंगल": {"emoji": "🔥", "importance": "medium", "desc": "मंगल का गोचर"},
    "सूर्य": {"emoji": "☀️", "importance": "medium", "desc": "सूर्य संक्रांति"},
    "शुक्र": {"emoji": "💫", "importance": "low",    "desc": "शुक्र का गोचर"},
    "बुध":  {"emoji": "📡", "importance": "low",    "desc": "बुध का गोचर"},
}

# ── Swiss Ephemeris Helpers ───────────────────────────────────────────
def _dt_to_jd(dt: datetime.datetime) -> float:
    tz = pytz.timezone("Asia/Kolkata")
    if dt.tzinfo is None:
        dt = tz.localize(dt)
    dt_utc = dt.astimezone(pytz.utc)
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day,
                      dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0)

def _get_rashi_idx(planet_id: int, jd: float) -> int:
    """किसी JD पर ग्रह की वैदिक (Lahiri) रashi index (0-11) लौटाता है"""
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    result, _ = swe.calc_ut(jd, planet_id, flags)
    return int(result[0] / 30) % 12

def get_current_gochar(jd: float) -> dict:
    """आज के सभी मुख्य ग्रहों की रashi dict में लौटाता है"""
    positions = {}
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    for naam, pid in MAIN_GOCHAR_PLANETS.items():
        flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
        result, _ = swe.calc_ut(jd, pid, flags)
        lon = result[0]
        rashi_idx = int(lon / 30) % 12
        positions[naam] = {
            "rashi": RASHI_NAMES[rashi_idx],
            "rashi_idx": rashi_idx,
            "degree": round(lon % 30, 2),
        }
    # केतु = राहु से 180°
    rahu_idx = positions["राहु"]["rashi_idx"]
    ketu_idx = (rahu_idx + 6) % 12
    positions["केतु"] = {
        "rashi": RASHI_NAMES[ketu_idx],
        "rashi_idx": ketu_idx,
        "degree": positions["राहु"]["degree"],
    }
    return positions

def get_yesterday_gochar(jd: float) -> dict:
    """कल के ग्रहों की position (आज से 1 दिन पहले)"""
    yesterday_jd = jd - 1.0
    return get_current_gochar(yesterday_jd)

def detect_gochar_changes(yesterday: dict, today: dict) -> list:
    """
    कल vs आज compare करके बताता है कौन से ग्रह ने रashi बदली।
    Returns: list of dicts — हर बदलाव की जानकारी
    """
    changes = []
    for graha in MAIN_GOCHAR_PLANETS.keys():
        old_rashi_idx = yesterday.get(graha, {}).get("rashi_idx", -1)
        new_rashi_idx = today.get(graha, {}).get("rashi_idx", -1)
        if old_rashi_idx != new_rashi_idx and old_rashi_idx != -1:
            changes.append({
                "graha": graha,
                "old_rashi": RASHI_NAMES[old_rashi_idx],
                "old_rashi_idx": old_rashi_idx,
                "new_rashi": RASHI_NAMES[new_rashi_idx],
                "new_rashi_idx": new_rashi_idx,
                "emoji": PLANET_INFO[graha]["emoji"],
                "importance": PLANET_INFO[graha]["importance"],
            })
    # केतु भी check करें (राहु के साथ automatically बदलता है)
    r_old = yesterday.get("केतु", {}).get("rashi_idx", -1)
    r_new = today.get("केतु", {}).get("rashi_idx", -1)
    if r_old != r_new and r_old != -1:
        changes.append({
            "graha": "केतु",
            "old_rashi": RASHI_NAMES[r_old],
            "old_rashi_idx": r_old,
            "new_rashi": RASHI_NAMES[r_new],
            "new_rashi_idx": r_new,
            "emoji": "☄️",
            "importance": "high",
        })
    return changes

# ── Gemini AI Call ────────────────────────────────────────────────────
def _call_gemini_gochar(prompt: str) -> str:
    if not GEMINI_API_KEYS:
        return ""
    keys = GEMINI_API_KEYS.copy()
    random.shuffle(keys)
    for api_key in keys[:3]:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{GEMINI_MODEL}:generateContent?key={api_key}")
        try:
            resp = requests.post(
                url,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.75, "maxOutputTokens": 300}
                },
                timeout=25,
                verify=False
            )
            if resp.status_code == 200:
                text = (resp.json()
                        .get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "")
                        .strip())
                if text:
                    return re.sub(r'[*#]', '', text)
            elif resp.status_code == 429:
                time.sleep(2)
        except Exception:
            time.sleep(1)
    return ""

# ── AI Prompt Builder ─────────────────────────────────────────────────
def build_gochar_prompt(user_name, profile, natal_pos, lagna_idx, dasha, change: dict) -> str:
    today_str = datetime.date.today().strftime("%d %B %Y")
    chandra_rashi = natal_pos.get("चंद्र", {}).get("rashi", "अज्ञात")
    chandra_nak   = natal_pos.get("चंद्र", {}).get("nakshatra", "")
    lagna_name    = RASHI_NAMES[lagna_idx] if 0 <= lagna_idx < 12 else "अज्ञात"
    
    graha      = change["graha"]
    old_rashi  = change["old_rashi"]
    new_rashi  = change["new_rashi"]
    new_r_idx  = change["new_rashi_idx"]
    
    # चंद्र राशि से गोचर भाव निकालें (1 से 12)
    chandra_idx = natal_pos.get("चंद्र", {}).get("rashi_idx", 0)
    bhava = ((new_r_idx - chandra_idx) % 12) + 1

    return f"""
आज की तारीख: {today_str}
आप एक वरिष्ठ वैदिक ज्योतिषी हैं।

गोचर परिवर्तन की घटना:
  ग्रह: {graha}
  पुरानी रashi: {old_rashi} → नई रashi: {new_rashi}
  चंद्र राशि से भाव: {bhava}वाँ भाव

यूज़र की जन्म-कुंडली:
  नाम: {user_name}
  जन्म लग्न: {lagna_name}
  चंद्र राशि: {chandra_rashi} ({chandra_nak})
  महादशा: {dasha.get('md', 'अज्ञात')} | अंतर्दशा: {dasha.get('ad', 'अज्ञात')}
  पेशा: {profile.profession or 'सामान्य'}
  जीवन फोकस: {profile.primary_focus or 'सामान्य'}

नियम:
1. सिर्फ 4-5 पंक्तियाँ — संक्षिप्त और सटीक।
2. '{user_name} जी,' से शुरू करें।
3. {graha} का {new_rashi} में प्रवेश उनके जीवन पर क्या प्रभाव डालेगा — {bhava}वें भाव के अनुसार स्पष्ट बताएं।
4. एक व्यावहारिक उपाय जरूर दें।
5. सकारात्मक और प्रेरक भाषा में लिखें।
"""

# ── Fallback Message ──────────────────────────────────────────────────
def build_fallback_message(user_name: str, change: dict) -> str:
    graha     = change["graha"]
    new_rashi = change["new_rashi"]
    emoji     = change["emoji"]
    return (f"{user_name} जी, आज {emoji} {graha} ने {new_rashi} राशि में प्रवेश किया है। "
            f"यह गोचर परिवर्तन आपके जीवन में नए प्रभाव लेकर आएगा। "
            f"इस समय ध्यान और सतर्कता बनाए रखें। 🙏")

# ── Main Process Function (master_cron.py द्वारा call होता है) ────────
def process_user_gochar(profile, kundali, natal_pos, lagna_idx, dasha, gochar_changes: list) -> int:
    """
    हर यूज़र के लिए gochar changes process करता है।
    Returns: नए बनाए गए notifications की संख्या
    """
    if not gochar_changes:
        return 0

    user_name = profile.user.first_name or profile.user.username
    today_str = datetime.date.today().strftime("%d %b %Y")
    new_count = 0

    for change in gochar_changes:
        graha     = change["graha"]
        new_rashi = change["new_rashi"]
        emoji     = change["emoji"]
        title     = f"{emoji} {graha} का {new_rashi} में प्रवेश ({today_str})"

        # Duplicate check — आज का यह अलर्ट पहले से है?
        if UserNotification.objects.filter(
            user=profile.user,
            title=title,
            notification_type='GOCHAR'
        ).exists():
            print(f"     ℹ️  {user_name}: {graha} गोचर अलर्ट पहले से मौजूद है। (Skip)")
            continue

        # Gemini से AI message लो
        prompt  = build_gochar_prompt(user_name, profile, natal_pos, lagna_idx, dasha, change)
        ai_msg  = _call_gemini_gochar(prompt)

        if not ai_msg:
            ai_msg = build_fallback_message(user_name, change)

        UserNotification.objects.create(
            user=profile.user,
            title=title,
            message=ai_msg,
            notification_type='GOCHAR'
        )
        print(f"     ✅ {user_name}: {graha} → {new_rashi} गोचर अलर्ट सेव हुआ।")
        new_count += 1

    return new_count


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# master_cron.py में उपयोग:
#
# from engines.gochar_alerts import get_current_gochar, get_yesterday_gochar,
#                                   detect_gochar_changes, process_user_gochar
#
# today_jd        = _dt_to_jd(now, "Asia/Kolkata")
# today_gochar    = get_current_gochar(today_jd)
# yesterday_gochar= get_yesterday_gochar(today_jd)
# gochar_changes  = detect_gochar_changes(yesterday_gochar, today_gochar)
#
# if gochar_changes:
#     print(f"  🪐 आज {len(gochar_changes)} ग्रह ने रashi बदली!")
#     for c in gochar_changes:
#         print(f"     {c['emoji']} {c['graha']}: {c['old_rashi']} → {c['new_rashi']}")
#
# # User loop में:
# is_gochar_new = process_user_gochar(profile, kundali, natal_pos,
#                                     lagna_idx, dasha, gochar_changes)
# notifications_generated_today += is_gochar_new
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
