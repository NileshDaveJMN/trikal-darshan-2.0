import swisseph as swe
import pytz, datetime, os, requests, random, re, time

GEMINI_API_KEYS = []
for i in range(1, 10):
    key = os.getenv(f"GEMINI_API_KEYS{i}", "").strip()
    if key:
        GEMINI_API_KEYS.append(key)

# नया मॉडल जो आपके दूसरे फंक्शन में चल रहा है
GEMINI_MODEL = "gemini-3-flash-preview"

RASHI_LIST = [
    {"id": "mesh",      "name": "मेष",      "symbol": "♈", "lord": "मंगल",  "idx": 0},
    {"id": "vrishabh",  "name": "वृषभ",     "symbol": "♉", "lord": "शुक्र", "idx": 1},
    {"id": "mithun",    "name": "मिथुन",    "symbol": "♊", "lord": "बुध",   "idx": 2},
    {"id": "kark",      "name": "कर्क",     "symbol": "♋", "lord": "चंद्र", "idx": 3},
    {"id": "sinh",      "name": "सिंह",     "symbol": "♌", "lord": "सूर्य", "idx": 4},
    {"id": "kanya",     "name": "कन्या",    "symbol": "♍", "lord": "बुध",   "idx": 5},
    {"id": "tula",      "name": "तुला",     "symbol": "♎", "lord": "शुक्र", "idx": 6},
    {"id": "vrishchik", "name": "वृश्चिक",  "symbol": "♏", "lord": "मंगल",  "idx": 7},
    {"id": "dhanu",     "name": "धनु",      "symbol": "♐", "lord": "गुरु",  "idx": 8},
    {"id": "makar",     "name": "मकर",      "symbol": "♑", "lord": "शनि",   "idx": 9},
    {"id": "kumbh",     "name": "कुंभ",     "symbol": "♒", "lord": "शनि",   "idx": 10},
    {"id": "meen",      "name": "मीन",      "symbol": "♓", "lord": "गुरु",  "idx": 11},
]

RASHI_NAMES_HI = [r["name"] for r in RASHI_LIST]

# ── Cache: store today's rashifal in memory ──────────────────────────
_rashifal_cache = {}   # { "mesh_2026-06-04": { GENERAL:..., CAREER:... } }

def _get_transit_summary():
    """Get today's planetary positions using Swisseph"""
    try:
        now = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
        jd  = swe.julday(now.year, now.month, now.day,
                         now.hour + now.minute/60.0)
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        ayan = swe.get_ayanamsa_ut(jd)

        planets = {
            "सूर्य": swe.SUN, "चंद्र": swe.MOON, "मंगल": swe.MARS,
            "बुध": swe.MERCURY, "गुरु": swe.JUPITER, "शुक्र": swe.VENUS,
            "शनि": swe.SATURN, "राहु": swe.TRUE_NODE,
        }
        lines = []
        for name, pid in planets.items():
            lon = (swe.calc_ut(jd, pid, swe.FLG_SWIEPH)[0][0] - ayan) % 360
            rashi_idx = int(lon / 30)
            lines.append(f"{name}: {RASHI_NAMES_HI[rashi_idx]} ({lon%30:.1f}°)")

        # Ketu = opposite Rahu
        rahu_lon = (swe.calc_ut(jd, swe.TRUE_NODE, swe.FLG_SWIEPH)[0][0] - ayan) % 360
        ketu_lon  = (rahu_lon + 180) % 360
        lines.append(f"केतु: {RASHI_NAMES_HI[int(ketu_lon/30)]} ({ketu_lon%30:.1f}°)")

        return "\n".join(lines)
    except Exception as e:
        return f"ग्रह स्थिति उपलब्ध नहीं: {e}"


def _call_gemini(prompt, max_retries=3):
    """Try Gemini API keys with updated model and retry logic"""
    if not GEMINI_API_KEYS: 
        return None
        
    keys = GEMINI_API_KEYS.copy()
    random.shuffle(keys)

    for attempt, api_key in enumerate(keys[:max_retries], 1):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}"
        try:
            resp = requests.post(
                url, 
                json={
                    "contents": [{"parts": [{"text": prompt}]}], 
                    "generationConfig": {"temperature": 0.75}
                }, 
                timeout=30, 
                verify=False
            )
            
            if resp.status_code == 200:
                # Safe parsing using .get() to prevent KeyError
                text = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                # Remove Markdown stars and hashes safely
                return re.sub(r'[*#]', '', text) if text else None
            elif resp.status_code == 429: 
                # Handle Too Many Requests
                time.sleep(2)
        except Exception: 
            time.sleep(1)
            
    return None


def _generate_rashifal(rashi_name, rashi_lord, transit):
    today = datetime.datetime.now().strftime("%d %B, %Y")
    prompt = f"""
आज की तारीख: {today}
आप एक अनुभवी वैदिक ज्योतिषी हैं।

{rashi_name} राशि (स्वामी: {rashi_lord}) का आज का राशिफल लिखें।

आज के ग्रहों की स्थिति:
{transit}

नीचे दिए गए विषयों पर 2-3 वाक्यों में सकारात्मक और व्यावहारिक मार्गदर्शन दें:
[GENERAL] सामान्य दिन कैसा रहेगा
[CAREER] करियर और व्यापार
[LOVE] प्रेम और रिश्ते
[HEALTH] स्वास्थ्य
[LUCKY] शुभ रंग, अंक और समय
[UPAY] आज का एक सरल उपाय

नियम:
- केवल हिंदी में लिखें
- कोई Markdown (**, ##) न हो
- सकारात्मक और उत्साहवर्धक भाषा में लिखें
- हर विषय [TAG] से शुरू करें
"""
    raw = _call_gemini(prompt)
    if not raw:
        return None

    result = {}
    for tag in ["GENERAL", "CAREER", "LOVE", "HEALTH", "LUCKY", "UPAY"]:
        m = re.search(rf"\[{tag}\][:\s]*(.*?)(?=\[|$)", raw, re.DOTALL)
        result[tag] = m.group(1).strip() if m else ""
    return result


# ── Main API View ─────────────────────────────────────────────────────
def api_rashifal(request):
    from django.http import JsonResponse
    rashi_id = request.GET.get("rashi_id", "").strip()
    rashi    = next((r for r in RASHI_LIST if r["id"] == rashi_id), None)

    if not rashi:
        return JsonResponse({"success": False, "error": "अमान्य राशि"})

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    cache_key = f"{rashi_id}_{today_str}"

    # Serve from cache if available
    if cache_key in _rashifal_cache:
        return JsonResponse({"success": True, **_rashifal_cache[cache_key]})

    # Generate fresh
    transit = _get_transit_summary()
    data    = _generate_rashifal(rashi["name"], rashi["lord"], transit)

    if not data:
        return JsonResponse({"success": False,
                             "error": "AI सेवा उपलब्ध नहीं। थोड़ी देर बाद प्रयास करें।"})

    _rashifal_cache[cache_key] = data
    return JsonResponse({"success": True, **data})


# ── Page Views ────────────────────────────────────────────────────────
def rashifal_home(request):
    from django.shortcuts import render
    today = datetime.datetime.now().strftime("%d %B, %Y")
    return render(request, "rashifal.html", {"rashis": RASHI_LIST, "today": today})


def rashifal_detail(request, rashi_id):
    from django.shortcuts import render
    rashi = next((r for r in RASHI_LIST if r["id"] == rashi_id), None)
    today = datetime.datetime.now().strftime("%d %B, %Y")
    if not rashi:
        return render(request, "rashifal.html", {"rashis": RASHI_LIST, "today": today})
    return render(request, "rashifal_detail.html",
                  {"rashi": rashi, "rashis": RASHI_LIST, "today": today})
