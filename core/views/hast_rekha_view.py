# core/views/hast_rekha_view.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# हस्त रेखा विश्लेषण — Gemini Vision से AI Palmistry
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import os
import re
import base64
import random
import time
import requests
import urllib3
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from core.models import UserProfile, HastRekhaReading

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Gemini API Setup ──────────────────────────────────────────────────
GEMINI_API_KEYS = []
for _i in range(1, 10):
    _k = os.environ.get(f"GEMINI_API_KEYS{_i}", "").strip()
    if _k:
        GEMINI_API_KEYS.append(_k)
GEMINI_VISION_MODEL = "gemini-3-flash-preview"

# ── Gemini Vision Call ────────────────────────────────────────────────
def _analyze_hand_with_gemini(image_base64: str, mime_type: str, user_name: str, profile) -> str:
    if not GEMINI_API_KEYS:
        return ""

    prompt = f"""
आप एक विद्वान वैदिक हस्त रेखा शास्त्री हैं जिन्हें 30 वर्षों का अनुभव है। 
इस हाथ की तस्वीर का अत्यंत सूक्ष्म निरीक्षण करें और पाराशरी सिद्धांतों के आधार पर विश्लेषण करें।

व्यक्ति का नाम: {user_name}
पेशा: {profile.profession or 'अज्ञात'}
जीवन फोकस: {profile.primary_focus or 'सामान्य'}

कृपया निम्न क्रम में विस्तृत विश्लेषण करें:

1. 🖐️ **हाथ की बनावट और अंगूठा:** (हाथ का प्रकार- भूमि/वायु/अग्नि/जल, और अंगूठे से व्यक्ति की इच्छाशक्ति व स्वभाव)

2. 🏔️ **प्रमुख पर्वत (Mounts):** (गुरु, शुक्र, सूर्य या बुध पर्वत में से जो भी सबसे ज्यादा उभरा हुआ या प्रभावशाली दिख रहा हो, उसका फल)

3. ❤️ **हृदय रेखा:** (प्रेम, भावनाएं और रिश्तों में व्यक्ति का रवैया)

4. 🧠 **मस्तिष्क रेखा:** (बुद्धि, निर्णय क्षमता, और {user_name} जी के वर्तमान पेशे/करियर से इसका क्या संबंध है)

5. 🌱 **जीवन रेखा:** (स्वास्थ्य, ऊर्जा और जीवन की गुणवत्ता)

6. ⭐ **भाग्य रेखा और सफलता:** (करियर में स्थिरता, धन लाभ और भाग्य का साथ)

7. 🌟 **विशेष चिन्ह:** (यदि कोई त्रिकोण, क्रॉस, द्वीप, या धन त्रिकोण (Money Triangle) स्पष्ट रूप से दिख रहा हो)

8. 🔮 **समग्र भविष्यवाणी और सार:** — {user_name} जी के 'जीवन फोकस' को ध्यान में रखते हुए एक व्यक्तिगत संदेश।

नियम (Strict Rules):
- हिंदी भाषा में लिखें और '{user_name} जी' से सम्मानपूर्वक संबोधन करें।
- **हवा में बात न करें:** जो रेखा या पर्वत जैसी दिख रही है, उसका कारण बताकर फलित करें (उदाहरण: "चूंकि आपकी मस्तिष्क रेखा सीधी है, इसलिए...")।
- प्रत्येक खंड में 2-3 सारगर्भित और स्पष्ट वाक्य हों।
- भाषा अत्यंत सकारात्मक, पेशेवर और मार्गदर्शक होनी चाहिए।
- अंत में उनके ग्रहों/रेखाओं के अनुसार एक विशिष्ट 'वैदिक उपाय' या 'मंत्र' जरूर दें।
- यदि तस्वीर में कोई विशिष्ट रेखा स्पष्ट नहीं दिख रही है, तो गलत अनुमान लगाने के बजाय विनम्रता से बताएं कि "तस्वीर में यह रेखा स्पष्ट नहीं है।"
"""


    keys = GEMINI_API_KEYS.copy()
    random.shuffle(keys)

    for api_key in keys[:3]:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{GEMINI_VISION_MODEL}:generateContent?key={api_key}")
        try:
            payload = {
                "contents": [{
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": image_base64
                            }
                        },
                        {"text": prompt}
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 1500
                }
            }
            resp = requests.post(url, json=payload, timeout=40, verify=False)
            if resp.status_code == 200:
                text = (resp.json()
                        .get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "")
                        .strip())
                if text:
                    return text
            elif resp.status_code == 429:
                time.sleep(2)
            else:
                # 🚀 यह 2 लाइनें हमें असल बीमारी बताएंगी!
                print(f"❌ [HastRekha] API Error Code: {resp.status_code}")
                print(f"❌ [HastRekha] API Response: {resp.text}")
                
        except Exception as e:
            print(f"[HastRekha] Gemini error: {e}")
            time.sleep(1)

    return ""


# ── Main View ─────────────────────────────────────────────────────────
@login_required
def hast_rekha_view(request):
    profile = UserProfile.objects.get(user=request.user)

    # Premium check
    if not profile.is_premium:
        return render(request, 'hast_rekha.html', {
            'is_premium': False,
            'readings': []
        })

    # Reading history
    readings = HastRekhaReading.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]

    return render(request, 'hast_rekha.html', {
        'is_premium': True,
        'readings': readings,
        'readings_count': readings.count()
    })


# ── API: Image Upload & Analyze ───────────────────────────────────────
@login_required
@require_POST
def api_analyze_hast_rekha(request):
    profile = UserProfile.objects.get(user=request.user)

    # Premium check
    if not profile.is_premium:
        return JsonResponse({
            'success': False,
            'error': 'यह सुविधा केवल प्रीमियम सदस्यों के लिए है।'
        }, status=403)

    # Image check
    image_file = request.FILES.get('hand_image')
    if not image_file:
        return JsonResponse({
            'success': False,
            'error': 'कृपया हाथ की तस्वीर अपलोड करें।'
        }, status=400)

    # File size check (max 5MB)
    if image_file.size > 5 * 1024 * 1024:
        return JsonResponse({
            'success': False,
            'error': 'तस्वीर का आकार 5MB से कम होना चाहिए।'
        }, status=400)

    # File type check
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
    mime_type = image_file.content_type
    if mime_type not in allowed_types:
        return JsonResponse({
            'success': False,
            'error': 'केवल JPG, PNG, या WEBP फ़ाइल अपलोड करें।'
        }, status=400)

    # Base64 encode — Gemini ko bhejo, server pe save mat karo
    image_data = image_file.read()
    image_base64 = base64.b64encode(image_data).decode('utf-8')
    del image_data  # Memory free karo

    user_name = request.user.first_name or request.user.username

    # Gemini Vision se analyze karo
    prediction = _analyze_hand_with_gemini(image_base64, mime_type, user_name, profile)
    del image_base64  # Image discard — store nahi karni

    if not prediction:
        return JsonResponse({
            'success': False,
            'error': 'विश्लेषण में समस्या आई। कृपया स्पष्ट तस्वीर के साथ पुनः प्रयास करें।'
        }, status=500)

    # Sirf prediction DB mein save karo
    reading = HastRekhaReading.objects.create(
        user=request.user,
        prediction=prediction,
        hand_type=request.POST.get('hand_type', 'दाहिना हाथ')
    )

    return JsonResponse({
        'success': True,
        'reading_id': reading.id,
        'prediction': prediction,
        'created_at': reading.created_at.strftime('%d %B %Y, %I:%M %p')
    })


# ── API: Reading History Delete ───────────────────────────────────────
@login_required
@require_POST
def api_delete_hast_reading(request, reading_id):
    try:
        reading = HastRekhaReading.objects.get(id=reading_id, user=request.user)
        reading.delete()
        return JsonResponse({'success': True})
    except HastRekhaReading.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'नहीं मिला'}, status=404)
