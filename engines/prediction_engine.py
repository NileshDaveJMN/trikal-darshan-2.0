import requests
import time
import random
import re
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

GEMINI_API_KEYS = [
    "AIzaSyCbDsXKkrGSfBrUlTg73RQH-B8pGdsLiXE",
    "AIzaSyBCS_azZIoJiXwcOoJ5TV_uUVED2Qp14IQ",
    "AIzaSyALN983OFeimP4SSI-wZO0oeKSe-En2dyg"
]

P_HINDI = {"Sun": "सूर्य", "Moon": "चंद्र", "Mars": "मंगल", "Mercury": "बुध", "Jupiter": "गुरु", "Venus": "शुक्र", "Saturn": "शनि", "Rahu": "राहु", "Ketu": "केतु"}

TOPIC_MAP = {
    "SUMMARY": "🌟 कुंडली का सार", "CAREER": "💼 करियर और धन", "MARRIAGE": "❤️ विवाह और रिश्ते",
    "HEALTH": "🏥 स्वास्थ्य", "EDUCATION": "🎓 शिक्षा", "PROPERTY": "🏠 संपत्ति",
    "TRAVEL": "✈️ विदेश यात्रा", "DASHA": "⏳ वर्तमान दशा फल", "SPECIAL_QUERY": "🎯 समाधान"
}

def get_bhav_phal(p_degrees_raw, l_idx, sav_points=None, curr_dasha=None, selected_topics=None, custom_question=""):
    house_planets = {i: [] for i in range(1, 13)}
    for p_name, deg in p_degrees_raw.items():
        p_sign = int(deg / 30)
        h_num = (p_sign - l_idx) % 12 + 1 
        house_planets[h_num].append(f"{P_HINDI.get(p_name, p_name)} ({deg % 30:.1f}°)")

    prompt_data = "".join([f"B{i}: {', '.join(house_planets[i]) if house_planets[i] else 'E'}, SAV: {sav_points[i-1] if sav_points else 0}\n" for i in range(1, 13)])
    
    topics = selected_topics.copy() if selected_topics is not None else ["SUMMARY", "CAREER", "MARRIAGE", "DASHA"]
    if custom_question.strip() and "SPECIAL_QUERY" not in topics: topics.append("SPECIAL_QUERY")

    topic_instr = "".join([f"[{t}]\n" for t in topics])

    prompt = f"""वैदिक ज्योतिषी की तरह डेटा का विश्लेषण करें:
{prompt_data}
दशा: {curr_dasha['md']} - {curr_dasha['ad']}
प्रश्न: {custom_question}

नियम: 
1. हर विषय पर केवल 2-3 लाइन का सटीक फलित लिखें।
2. कोई Markdown (**, ##) न हो।
फॉर्मेट:
{topic_instr}
"""

    ai_responses = {t: "लोड हो रहा है..." for t in topics}
    last_error = "अज्ञात तकनीकी समस्या।"
    
    for attempt in range(2): 
        current_api_key = random.choice(GEMINI_API_KEYS)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={current_api_key}"
        
        try:
            response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=25, verify=False)
            if response.status_code == 200:
                res_json = response.json()
                
                if 'candidates' in res_json and res_json['candidates']:
                    candidate = res_json['candidates'][0]
                    if candidate.get('finishReason') == 'SAFETY':
                        last_error = "⚠️ AI ने सुरक्षा कारणों से जवाब रोक दिया है।"
                        break
                        
                    if 'content' in candidate and 'parts' in candidate['content']:
                        ai_text = candidate['content']['parts'][0]['text'].replace("**", "").replace("##", "")
                        
                        found_any = False
                        for t in topics:
                            pattern = rf"\[{t}\][\s:]*(.*?)(?=\[|$)"
                            match = re.search(pattern, ai_text, re.DOTALL | re.IGNORECASE)
                            if match: 
                                ai_responses[t] = match.group(1).strip()
                                found_any = True
                        
                        if not found_any and len(ai_text) > 10:
                            ai_responses[topics[0]] = ai_text.strip()
                            
                        final_preds = [{"planet_name": TOPIC_MAP.get(t, t), "text": f"<p style='color: #2c3e50; font-size: 15px;'>{ai_responses[t]}</p>"} for t in topics if t != "DASHA"]
                        return final_preds, ai_responses.get("DASHA", "दशा उपलब्ध नहीं है।")
                else:
                    last_error = "⚠️ AI ने खाली जवाब भेजा।"
            else:
                last_error = f"⚠️ API Error ({response.status_code}): {response.text}"
        except requests.exceptions.Timeout:
            last_error = "⚠️ AI विश्लेषण में बहुत समय ले रहा है (Timeout)।"
        except Exception as e:
            last_error = f"⚠️ Error: {str(e)}"
        
        time.sleep(1)

    ai_responses[topics[0]] = f"<div style='background:#fdedec; padding:15px; border-left:4px solid #e74c3c; border-radius:5px;'><b style='color:#c0392b;'>डायग्नोस्टिक रिपोर्ट:</b><br><span style='color:#34495e; font-size:14px;'>{last_error}</span></div>"
    
    final_preds = [{"planet_name": TOPIC_MAP.get(t, t), "text": f"<p style='color: #2c3e50; font-size: 15px;'>{ai_responses[t]}</p>"} for t in topics if t != "DASHA"]
    return final_preds, ai_responses.get("DASHA", last_error)
