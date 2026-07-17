import requests
import time
import datetime
import random
import re
import urllib3
import os
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 🌟 .env Auto-Load
_env_path = Path(__file__).parent / '.env'
if _env_path.exists():
    for _line in _env_path.read_text(encoding='utf-8').splitlines():
        _line = _line.strip()
        if _line and '=' in _line and not _line.startswith('#'):
            _k, _v = _line.split('=', 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# 🌟 GEMINI_API_KEYS1, KEYS2... सभी load करें
GEMINI_API_KEYS = []
for _i in range(1, 10):
    _key = os.getenv(f"GEMINI_API_KEYS{_i}", "").strip()
    if _key:
        GEMINI_API_KEYS.append(_key)

current_time = datetime.datetime.now()
month_year = current_time.strftime("%B %Y")

P_HINDI = {"Sun": "सूर्य", "Moon": "चंद्र", "Mars": "मंगल", "Mercury": "बुध", "Jupiter": "गुरु", "Venus": "शुक्र", "Saturn": "शनि", "Rahu": "राहु", "Ketu": "केतु"}

TOPIC_MAP = {
    "SUMMARY": "🌟 कुंडली का सार", "CAREER": "💼 करियर और धन", "MARRIAGE": "❤️ विवाह और रिश्ते",
    "HEALTH": "🏥 स्वास्थ्य", "EDUCATION": "🎓 शिक्षा", "PROPERTY": "🏠 संपत्ति",
    "TRAVEL": "✈️ विदेश यात्रा", "DASHA": "⏳ दशा विश्लेषण", "SPECIAL_QUERY": "🎯 समाधान"
}

def get_bhav_phal(p_degrees_raw, l_idx, sav_points=None, curr_dasha=None, selected_topics=None, custom_question=""):
    current_time = datetime.datetime.now()
    current_date_str = current_time.strftime("%d %B, %Y")
    month_year = current_time.strftime("%B %Y")

    RASHI_NAMES = ["मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"]
    lagna_name = RASHI_NAMES[l_idx]

    house_planets = {i: [] for i in range(1, 13)}
    planet_to_house = {} 
    
    for p_name, deg in p_degrees_raw.items():
        p_sign = int(deg / 30)
        h_num = (p_sign - l_idx) % 12 + 1 
        hindi_name = P_HINDI.get(p_name, p_name)
        
        house_planets[h_num].append(f"{hindi_name} ({deg % 30:.1f}°)")
        planet_to_house[hindi_name] = h_num

    drashti_info = []
    for p, h in planet_to_house.items():
        aspects = [(h + 7 - 1) % 12 + 1] 
        if p == "मंगल": 
            aspects.extend([(h + 4 - 1) % 12 + 1, (h + 8 - 1) % 12 + 1])
        elif p in ["गुरु", "राहु", "केतु"]: 
            aspects.extend([(h + 5 - 1) % 12 + 1, (h + 9 - 1) % 12 + 1])
        elif p == "शनि": 
            aspects.extend([(h + 3 - 1) % 12 + 1, (h + 10 - 1) % 12 + 1])
        
        unique_aspects = sorted(list(set(aspects)))
        drashti_info.append(f"{p} की दृष्टि भाव {', '.join(map(str, unique_aspects))} पर है।")

    prompt_data = "".join([f"भाव {i}: {', '.join(house_planets[i]) if house_planets[i] else 'खाली'}, SAV: {sav_points[i-1] if sav_points else 0}\n" for i in range(1, 13)])
    drashti_text = "\n".join(drashti_info)
    
    topics = selected_topics.copy() if selected_topics is not None else ["SUMMARY", "CAREER", "MARRIAGE", "DASHA"]
    if custom_question.strip() and "SPECIAL_QUERY" not in topics: topics.append("SPECIAL_QUERY")
    topic_instr = "".join([f"[{t}]\n" for t in topics])

    prompt = f"""
आज की तारीख: {current_date_str}

आप 30 साल के अनुभव वाले एक विशेषज्ञ और 'सकारात्मक मार्गदर्शक' (Constructive Guide) वैदिक ज्योतिषी हैं। 
नीचे दी गई कुण्डली का गहराई से, लेकिन अत्यंत संतुलित (Balanced) विश्लेषण करें:

कुण्डली का मूल विवरण:
- लग्न: {lagna_name}
- वर्तमान दशा: {curr_dasha['md']} महादशा - {curr_dasha['ad']} अंतर्दशा

ग्रहों की भाव स्थिति और SAV स्कोर:
{prompt_data}

ग्रहों की दृष्टियाँ (Aspects):
{drashti_text}

प्रश्न: {custom_question}

फलित के लिए नियम:
1. अत्यंत संतुलित दृष्टिकोण (Balanced Approach): केवल नकारात्मक (Negative) बातें न करें। अगर किसी भाव में कम SAV या नीच ग्रह के कारण चुनौती है, तो उसी कुण्डली में मौजूद शुभ ग्रहों की दृष्टि, उच्च ग्रहों या मजबूत योगों के कारण मिलने वाले अवसरों (Opportunities) को भी प्रमुखता से बताएं।
2. डराने के बजाय मार्गदर्शन दें: अगर कोई संघर्ष है, तो बताएं कि जातक अपनी किस ताकत (Strength) या शुभ ग्रह का इस्तेमाल करके उस से बाहर आ सकता है। 
3. ग्रहों की भाव स्थिति, डिग्री, SAV स्कोर और ऊपर दी गई दृष्टियों (Aspects) का सटीक उपयोग करें।
4. हर विषय पर 3-4 लाइन में स्पष्ट, निष्पक्ष और समाधान-केंद्रित (Solution-oriented) फलित लिखें। कोई Markdown (**, ##) न हो।
5. विशेष ध्यान: अभी {month_year} चल रहा है। आपकी गणना और समय-सीमा इसी महीने से आगे की होनी चाहिए। 2025 या पुराने समय की बात न करें।

फॉर्मेट:
{topic_instr}
"""
    ai_responses = {t: "AI गणना करने में असमर्थ रहा।" for t in topics}
    last_error = "सर्वर कोटा समाप्त। कृपया थोड़ी देर बाद प्रयास करें।"

    random.shuffle(GEMINI_API_KEYS)
    for attempt in range(len(GEMINI_API_KEYS)):
        current_api_key = GEMINI_API_KEYS[attempt]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={current_api_key}"

        try:
            response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30, verify=False)

            if response.status_code == 200:
                res_json = response.json()

                if 'candidates' in res_json and res_json['candidates']:
                    candidate = res_json['candidates'][0]
                    if candidate.get('finishReason') == 'SAFETY':
                        last_error = "⚠️ सुरक्षा फिल्टर ने जवाब रोक दिया है।"
                        continue

                    if 'content' in candidate and 'parts' in candidate['content']:
                        ai_text = candidate['content']['parts'][0]['text'].replace("**", "").replace("##", "")

                        found_any = False
                        for t in topics:
                            pattern = rf"\[{t}\][\s:]*(.*?)(?=\[|$)"
                            match = re.search(pattern, ai_text, re.DOTALL | re.IGNORECASE)
                            if match:
                                ai_responses[t] = match.group(1).strip()
                                found_any = True

                        if not found_any and len(ai_text) > 20:
                            ai_responses[topics[0]] = ai_text.strip()

                        final_preds = [
                            {
                                "topic_id": t,
                                "planet_name": TOPIC_MAP.get(t, t),
                                "text": f"<p style='color: #2c3e50; font-size: 15px;'>{ai_responses.get(t)}</p>"
                            }
                            for t in topics
                        ]

                        if not final_preds:
                            final_preds.append({
                                "topic_id": "DASHA",
                                "planet_name": "⏳ दशा विश्लेषण",
                                "text": f"<p style='color: #2c3e50; font-size: 15px;'>{ai_text[:200]}...</p>"
                            })

                        return final_preds, ai_responses.get("DASHA", "दशा विश्लेषण पूर्ण नहीं हुआ।")
                else:
                    last_error = "AI ने खाली रिस्पॉन्स भेजा।"
            else:
                last_error = f"API Error {response.status_code}: {response.text[:100]}"
        except requests.exceptions.Timeout:
            last_error = "AI सर्वर अभी धीमा जवाब दे रहा है। कृपया कुछ देर बाद पुनः प्रयास करें।"
        except Exception as e:
            last_error = "AI से जुड़ने में समस्या आई। कृपया पुनः प्रयास करें।"

        time.sleep(1)

    return [{"topic_id": "ERROR", "planet_name": "Error", "text": f"<div style='color:red;'>{last_error}</div>"}], last_error

def get_ai_chat_reply(kundali_name, kd, user_message, history_text):
    import datetime
    import requests
    import random
    
    current_date_str = datetime.datetime.now().strftime("%d %B, %Y")
    
    # 1. 🚀 सटीक भाव और ग्रह (House & Planet) Extraction
    # हम 'houses' लिस्ट से भाव निकालेंगे और 'planet_details' से डिग्री जोड़ेंगे
    house_planets = {i: [] for i in range(1, 13)}
    planet_to_house = {}
    
    # डिग्री निकालने के लिए planet_details का मैप बनाएं
    deg_map = {}
    for p in kd.get('planet_details', []):
        name = p.get('name', '').strip()
        degree = p.get('degree', '').strip()
        if name:
            deg_map[name] = degree

    for h in kd.get('houses', []):
        h_num = h.get('num')
        p_full = h.get('planets_full', '')
        
        # अगर भाव में ग्रह हैं (--- नहीं है)
        if h_num and p_full and p_full != "---":
            # ग्रहों के नाम कॉमा (,) से अलग होते हैं (e.g., "सूर्य, राहु")
            planet_names = [p.strip() for p in p_full.split(',')]
            for p_name in planet_names:
                if p_name:
                    deg = deg_map.get(p_name, "")
                    deg_str = f" ({deg})" if deg else ""
                    house_planets[h_num].append(f"{p_name}{deg_str}")
                    planet_to_house[p_name] = h_num

    # 2. 🚀 दृष्टियाँ (ASPECTS)
    drashti_info = []
    for p, h in planet_to_house.items():
        aspects = [(h + 7 - 1) % 12 + 1]
        if p == "मंगल": aspects.extend([(h + 4 - 1) % 12 + 1, (h + 8 - 1) % 12 + 1])
        elif p in ["गुरु", "राहु", "केतु"]: aspects.extend([(h + 5 - 1) % 12 + 1, (h + 9 - 1) % 12 + 1])
        elif p == "शनि": aspects.extend([(h + 3 - 1) % 12 + 1, (h + 10 - 1) % 12 + 1])
        
        unique_aspects = sorted(list(set(aspects)))
        drashti_info.append(f"{p} की दृष्टि भाव {', '.join(map(str, unique_aspects))} पर है।")

    prompt_data = "".join([f"भाव {i}: {', '.join(house_planets[i]) if house_planets[i] else 'खाली'}\n" for i in range(1, 13)])
    drashti_text = "\n".join(drashti_info)

    # 3. 🚀 सटीक दशा Extraction (is_current के आधार पर)
    m_dasha_name, a_dasha_name = "N/A", "N/A"
    for md in kd.get('dasha', []):
        if md.get('is_current'):
            m_dasha_name = md.get('planet', 'N/A')
            for ad in md.get('antardashas', []):
                if ad.get('is_current'):
                    a_dasha_name = ad.get('planet', 'N/A')
                    break
            break
            
    dasha_info = f"{m_dasha_name} महादशा - {a_dasha_name} अंतर्दशा"

    # 4. 🚀 प्रॉम्प्ट और AI कॉलिंग
    prompt = (
        f"आज की तारीख: {current_date_str}\n\n"
        "आप 30 साल के अनुभव वाले एक विशेषज्ञ और 'सकारात्मक मार्गदर्शक' (Constructive Guide) वैदिक ज्योतिषी हैं, आपका नाम 'Trikal AI' है।\n"
        f"कुण्डली: नाम: {kundali_name}, लग्न: {kd.get('lagna', 'N/A')}, चंद्र राशि: {kd.get('chandra_rashi', 'N/A')}, नक्षत्र: {kd.get('nakshatra', 'N/A')}, दशा: {dasha_info}\n\n"
        f"भाव स्थिति:\n{prompt_data}\n"
        f"दृष्टियाँ:\n{drashti_text}\n\n"
        f"=== पिछली बातचीत ===\n{history_text}\n\n"
        f"यूजर का प्रश्न: {user_message}\n\n"
        "नियम: 1. अत्यंत संतुलित दृष्टिकोण अपनाएं। 2. डराने के बजाय समाधान दें। 3. जवाब हिंदी में, साधारण और वार्म टोन में दें। कोई Markdown (**, ##) न हो।"
    )

    ai_reply = "माफ करें, AI सर्वर अभी व्यस्त है। कृपया कुछ देर बाद पुनः प्रयास करें।"
    
    # GEMINI_API_KEYS का उपयोग 
    # (अगर GEMINI_API_KEYS फाइल में ऊपर इम्पोर्टेड नहीं है, तो उसे यहाँ इम्पोर्ट करें)
    from engines.prediction_engine import GEMINI_API_KEYS 
    keys = GEMINI_API_KEYS.copy()
    random.shuffle(keys)
    
    for api_key in keys:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
        try:
            resp = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30, verify=False)
            if resp.status_code == 200:
                res_json = resp.json()
                candidates = res_json.get('candidates', [])
                if candidates and candidates[0].get('finishReason') != 'SAFETY':
                    parts = candidates[0].get('content', {}).get('parts', [])
                    if parts:
                        ai_reply = parts[0]['text'].replace("**", "").replace("##", "").strip()
                        break
        except Exception:
            continue
            
    return ai_reply
