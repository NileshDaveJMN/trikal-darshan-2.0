# engines/dasha_alerts.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# दशा परिवर्तन अलर्ट इंजन
# जब user की Mahadasha ya Antardasha badle, AI se personal alert bheje
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import os
import re
import random
import datetime
import time
import requests
import urllib3

from core.models import UserNotification
from engines.kundali_engine import get_vimshottari_dasha

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Gemini API Setup ──────────────────────────────────────────────────
GEMINI_API_KEYS = []
for _i in range(1, 10):
    _k = os.environ.get(f"GEMINI_API_KEYS{_i}", "").strip()
    if _k:
        GEMINI_API_KEYS.append(_k)
GEMINI_MODEL = "gemini-2.0-flash-exp"

# ── Constants ─────────────────────────────────────────────────────────
RASHI_NAMES = ["मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या",
               "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"]

# दशा स्वामियों के गुण
DASHA_PHAL = {
    "सूर्य":  {"emoji": "☀️", "nature": "सत्ता, मान-सम्मान, पिता, सरकारी कार्य"},
    "चंद्र":  {"emoji": "🌙", "nature": "मन, माता, भावनाएं, यात्रा"},
    "मंगल":  {"emoji": "🔥", "nature": "साहस, भूमि, भाई, विवाद"},
    "राहु":  {"emoji": "🌑", "nature": "अचानक परिवर्तन, विदेश, भ्रम"},
    "गुरु":  {"emoji": "🌟", "nature": "ज्ञान, संतान, धर्म, गुरु"},
    "शनि":  {"emoji": "🪐", "nature": "कर्म, मेहनत, देरी, न्याय"},
    "बुध":  {"emoji": "📡", "nature": "बुद्धि, व्यापार, संचार"},
    "केतु":  {"emoji": "☄️", "nature": "आध्यात्म, मोक्ष, रहस्य"},
    "शुक्र":  {"emoji": "💫", "nature": "प्रेम, सौंदर्य, विलास, धन"},
}

# ── Gemini AI Call ────────────────────────────────────────────────────
def _call_gemini_dasha(prompt: str) -> str:
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
                    "generationConfig": {"temperature": 0.8, "maxOutputTokens": 350}
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

# ── Dasha Change Detection ────────────────────────────────────────────
def detect_dasha_change(kundali) -> dict:
    """
    Aaj ki dasha check karke batata hai koi change hua ya nahi.
    Returns: {
        'md_changed': bool,
        'ad_changed': bool,
        'current_md': str,
        'current_ad': str,
        'md_end': str,
        'ad_end': str,
        'prev_md': str,  (sirf tab jab change hua ho)
        'prev_ad': str,  (sirf tab jab change hua ho)
    }
    """
    try:
        import swisseph as swe
        import pytz

        dt_ist = datetime.datetime(
            kundali.year, kundali.month, kundali.day,
            kundali.hour, kundali.minute, kundali.second
        )
        dt_utc = dt_ist - datetime.timedelta(hours=5, minutes=30)
        jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day,
                        dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0)
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        moon_deg = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)[0][0]

        today = datetime.datetime.now()
        yesterday = today - datetime.timedelta(days=1)

        # Aaj ki dasha
        _, today_dasha   = get_vimshottari_dasha(moon_deg, dt_ist)
        
        # Kal ki dasha simulate karne ke liye datetime.now() ko override nahi kar sakte
        # Isliye antardasha end dates check karte hain
        dasha_list, _ = get_vimshottari_dasha(moon_deg, dt_ist)

        result = {
            "md_changed": False,
            "ad_changed": False,
            "current_md": today_dasha.get("md", "अज्ञात"),
            "current_ad": today_dasha.get("ad", "अज्ञात"),
            "md_end": "-",
            "ad_end": "-",
            "prev_md": "",
            "prev_ad": "",
        }

        for i, md in enumerate(dasha_list):
            if md["is_current"]:
                result["md_end"] = md["end"]

                # MD change check: kya aaj MD start hua? (start date aaj hai)
                md_start = datetime.datetime.strptime(md["start"], "%d-%m-%Y")
                if md_start.date() == today.date():
                    result["md_changed"] = True
                    # Pichli MD
                    if i > 0:
                        result["prev_md"] = dasha_list[i - 1]["planet"]

                for j, ad in enumerate(md["antardashas"]):
                    if ad["is_current"]:
                        result["ad_end"] = ad["end"]

                        # AD change check: kya aaj AD start hua?
                        ad_start = datetime.datetime.strptime(ad["start"], "%d-%m-%Y")
                        if ad_start.date() == today.date():
                            result["ad_changed"] = True
                            if j > 0:
                                result["prev_ad"] = md["antardashas"][j - 1]["planet"]
                            elif i > 0:
                                # Pichli MD ki last antardasha
                                prev_ads = dasha_list[i - 1]["antardashas"]
                                if prev_ads:
                                    result["prev_ad"] = prev_ads[-1]["planet"]
                        break
                break

        return result

    except Exception as e:
        print(f"     ⚠️ Dasha detect error: {e}")
        return {"md_changed": False, "ad_changed": False,
                "current_md": "अज्ञात", "current_ad": "अज्ञात",
                "md_end": "-", "ad_end": "-", "prev_md": "", "prev_ad": ""}

# ── AI Prompt Builders ────────────────────────────────────────────────
def build_md_change_prompt(user_name, profile, natal_pos, lagna_idx, dasha_info) -> str:
    today_str  = datetime.date.today().strftime("%d %B %Y")
    new_md     = dasha_info["current_md"]
    prev_md    = dasha_info.get("prev_md", "पिछली")
    md_end     = dasha_info["md_end"]
    current_ad = dasha_info["current_ad"]
    lagna_name = RASHI_NAMES[lagna_idx] if 0 <= lagna_idx < 12 else "अज्ञात"
    chandra_r  = natal_pos.get("चंद्र", {}).get("rashi", "अज्ञात")
    md_info    = DASHA_PHAL.get(new_md, {"nature": "सामान्य"})

    return f"""
आज की तारीख: {today_str}
आप एक वरिष्ठ वैदिक ज्योतिषी हैं।

महत्वपूर्ण घटना — महादशा परिवर्तन:
  पुरानी महादशा: {prev_md}
  नई महादशा: {new_md} (आज से प्रारंभ, समाप्ति: {md_end})
  वर्तमान अंतर्दशा: {current_ad}
  {new_md} का स्वभाव: {md_info['nature']}

यूज़र की जन्म-कुंडली:
  नाम: {user_name}
  जन्म लग्न: {lagna_name}
  चंद्र राशि: {chandra_r}
  पेशा: {profile.profession or 'सामान्य'}
  जीवन फोकस: {profile.primary_focus or 'सामान्य'}
  वैवाहिक स्थिति: {profile.relationship_status or 'अज्ञात'}

नियम:
1. 5-6 पंक्तियाँ — गहरा और व्यक्तिगत संदेश।
2. '{user_name} जी,' से शुरू करें।
3. {new_md} महादशा का उनके जीवन पर क्या प्रभाव पड़ेगा — लग्न और चंद्र राशि के अनुसार बताएं।
4. इस दशा में क्या सावधानियां रखें और क्या अवसर मिलेंगे।
5. एक विशेष उपाय या मंत्र जरूर बताएं।
6. प्रेरक और सकारात्मक भाषा में लिखें।
"""

def build_ad_change_prompt(user_name, profile, natal_pos, lagna_idx, dasha_info) -> str:
    today_str = datetime.date.today().strftime("%d %B %Y")
    current_md = dasha_info["current_md"]
    new_ad     = dasha_info["current_ad"]
    prev_ad    = dasha_info.get("prev_ad", "पिछली")
    ad_end     = dasha_info["ad_end"]
    lagna_name = RASHI_NAMES[lagna_idx] if 0 <= lagna_idx < 12 else "अज्ञात"
    chandra_r  = natal_pos.get("चंद्र", {}).get("rashi", "अज्ञात")
    ad_info    = DASHA_PHAL.get(new_ad, {"nature": "सामान्य"})

    return f"""
आज की तारीख: {today_str}
आप एक वरिष्ठ वैदिक ज्योतिषी हैं।

महत्वपूर्ण घटना — अंतर्दशा परिवर्तन:
  वर्तमान महादशा: {current_md}
  पुरानी अंतर्दशा: {prev_ad}
  नई अंतर्दशा: {new_ad} (आज से प्रारंभ, समाप्ति: {ad_end})
  {new_ad} का स्वभाव: {ad_info['nature']}

यूज़र की जन्म-कुंडली:
  नाम: {user_name}
  जन्म लग्न: {lagna_name}
  चंद्र राशि: {chandra_r}
  पेशा: {profile.profession or 'सामान्य'}
  जीवन फोकस: {profile.primary_focus or 'सामान्य'}

नियम:
1. 4-5 पंक्तियाँ — संक्षिप्त और सटीक।
2. '{user_name} जी,' से शुरू करें।
3. {current_md} महादशा में {new_ad} अंतर्दशा का विशेष प्रभाव बताएं।
4. एक व्यावहारिक उपाय जरूर दें।
5. सकारात्मक भाषा में लिखें।
"""

# ── Main Process Function ─────────────────────────────────────────────
def process_user_dasha(profile, kundali, natal_pos, lagna_idx) -> int:
    """
    User ki dasha check karke notification bhejta hai agar aaj change hua ho.
    Returns: naye notifications ki sankhya
    """
    user_name  = profile.user.first_name or profile.user.username
    today_str  = datetime.date.today().strftime("%d %b %Y")
    new_count  = 0

    dasha_info = detect_dasha_change(kundali)

    # ── A. Mahadasha Parivartan ──
    if dasha_info["md_changed"]:
        new_md = dasha_info["current_md"]
        emoji  = DASHA_PHAL.get(new_md, {}).get("emoji", "🔮")
        title  = f"{emoji} {new_md} महादशा प्रारंभ ({today_str})"

        if not UserNotification.objects.filter(
            user=profile.user, title=title, notification_type='DASHA'
        ).exists():
            prompt = build_md_change_prompt(user_name, profile, natal_pos, lagna_idx, dasha_info)
            ai_msg = _call_gemini_dasha(prompt)

            if not ai_msg:
                ai_msg = (f"{user_name} जी, आज से आपकी {new_md} महादशा प्रारंभ हो रही है। "
                          f"यह दशा {dasha_info['md_end']} तक रहेगी। "
                          f"इस समय {DASHA_PHAL.get(new_md, {}).get('nature', '')} से संबंधित विषयों पर ध्यान दें। 🙏")

            UserNotification.objects.create(
                user=profile.user,
                title=title,
                message=ai_msg,
                notification_type='DASHA'
            )
            print(f"     ✅ {user_name}: {new_md} महादशा अलर्ट सेव हुआ।")
            new_count += 1

    # ── B. Antardasha Parivartan ──
    if dasha_info["ad_changed"]:
        new_ad    = dasha_info["current_ad"]
        current_md = dasha_info["current_md"]
        emoji     = DASHA_PHAL.get(new_ad, {}).get("emoji", "🔮")
        title     = f"{emoji} {current_md}/{new_ad} अंतर्दशा प्रारंभ ({today_str})"

        if not UserNotification.objects.filter(
            user=profile.user, title=title, notification_type='DASHA'
        ).exists():
            prompt = build_ad_change_prompt(user_name, profile, natal_pos, lagna_idx, dasha_info)
            ai_msg = _call_gemini_dasha(prompt)

            if not ai_msg:
                ai_msg = (f"{user_name} जी, आज से {current_md} महादशा में {new_ad} अंतर्दशा प्रारंभ हो रही है। "
                          f"यह {dasha_info['ad_end']} तक रहेगी। "
                          f"इस समय {DASHA_PHAL.get(new_ad, {}).get('nature', '')} पर विशेष ध्यान दें। 🙏")

            UserNotification.objects.create(
                user=profile.user,
                title=title,
                message=ai_msg,
                notification_type='DASHA'
            )
            print(f"     ✅ {user_name}: {current_md}/{new_ad} अंतर्दशा अलर्ट सेव हुआ।")
            new_count += 1

    if new_count == 0:
        print(f"     ℹ️  {user_name}: आज कोई दशा परिवर्तन नहीं है। (Skip)")

    return new_count


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# master_cron.py में उपयोग:
#
# from engines.dasha_alerts import process_user_dasha
#
# # User loop में (natal_pos, lagna_idx पहले से calculate हैं):
# dasha_new = process_user_dasha(profile, kundali, natal_pos, lagna_idx)
# notifications_generated_today += dasha_new
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
