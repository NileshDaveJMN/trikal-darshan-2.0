import os
import sys
import datetime
import time
import pytz
from pathlib import Path

# ── 1. Django Setup (Standalone स्क्रिप्ट्स के लिए ज़रूरी) ──
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trikal_portal.settings')
import django
django.setup()

from core.models import UserProfile, SavedKundali, PushSubscription
from core.views.push_views import send_push_to_user

# ── 2. आज़ाद मॉड्यूल्स (Engines) इम्पोर्ट करना ──
from engines.daily_horoscope import (
    pre_generate_12_rashifal, 
    _dt_to_jd, 
    calculate_transit_positions, 
    calculate_natal_positions, 
    calculate_lagna, 
    build_dasha_info,
    process_user_horoscope
)
from engines.festival_alerts import (
    get_today_panchang, 
    get_today_festivals, 
    process_user_festival
)

def run_master_engine():
    print("\n" + "━" * 60)
    print("  🚀 Trikal Darshan - Master AI Engine (v1.0)")
    print("━" * 60)

    # ── STEP 1: One-time Global Calculations (वन-टाइम ग्लोबल कैलकुलेशन) ──
    print("\n  🌍 1. ग्लोबल डेटा (पंचांग, गोचर और 12 राशियां) तैयार किया जा रहा है...")
    
    # a. 12 राशियों का सामान्य राशिफल (Pre-caching)
    pre_generate_12_rashifal()

    # b. आज का पंचांग और त्यौहार
    panchang = get_today_panchang()
    today_festivals = get_today_festivals(panchang) if panchang else []
    
    if today_festivals:
        print(f"  🎉 आज के त्यौहार ({len(today_festivals)}):")
        for f in today_festivals:
            print(f"     - {f.get('emoji', '')} {f['name']}")
    else:
        print("  ℹ️ आज कोई विशेष पर्व नहीं है।")

    # c. आज का गोचर (Transit Positions)
    tz = pytz.timezone("Asia/Kolkata")
    now = datetime.datetime.now(tz)
    today_jd = _dt_to_jd(now, "Asia/Kolkata")
    today_transit = calculate_transit_positions(today_jd)

    profiles = UserProfile.objects.select_related("user").all()
    print(f"\n  👥 2. कुल सक्रिय यूज़र्स की प्रोसेसिंग शुरू: {profiles.count()}")

    sent_users_count = 0

    # ── STEP 2: User Loop (हर यूज़र के लिए) ──
    for profile in profiles:
        user_name = profile.user.first_name or profile.user.username
        kundali = SavedKundali.objects.filter(user=profile.user).order_by("created_at").first()
        
        if not kundali:
            continue
            
        print(f"\n  👤 प्रोसेसिंग: {user_name} ({profile.user.username})")

        # यूज़र की जन्म कुंडली (Natal) सिर्फ 1 बार निकालें
        natal_pos, natal_jd = calculate_natal_positions(kundali)
        lagna_idx = calculate_lagna(natal_jd, kundali.lat, kundali.lon)
        dasha = build_dasha_info(kundali)

        notifications_generated_today = 0

        # ── STEP 3: आज़ाद मॉड्यूल्स (Independent Modules) को काम सौंपना ──
        
        # A. दैनिक राशिफल मॉड्यूल
        is_horoscope_new = process_user_horoscope(profile, kundali, natal_pos, lagna_idx, dasha, today_transit)
        if is_horoscope_new:
            notifications_generated_today += 1

        # B. त्यौहार अलर्ट मॉड्यूल (अगर आज कोई त्यौहार है)
        if today_festivals:
            # हम सिर्फ पहले/मुख्य त्यौहार का मैसेज भेजेंगे ताकि AI API स्पैम न हो
            main_festival = today_festivals[0]
            is_festival_new = process_user_festival(profile, kundali, natal_pos, lagna_idx, dasha, main_festival)
            if is_festival_new:
                notifications_generated_today += 1

        # ── STEP 4: स्मार्ट सिंगल पुश नोटिफिकेशन ──
        # अगर आज इस यूज़र के लिए कोई भी नया मैसेज बना है, तो सिर्फ 1 पुश भेजो
        if notifications_generated_today > 0:
            subs = PushSubscription.objects.filter(user=profile.user, is_active=True)
            if subs.exists():
                push_title = "✨ त्रिकाल दर्शन अपडेट"
                
                if notifications_generated_today == 1:
                    push_msg = f"सुप्रभात {user_name} जी! आपका आज का व्यक्तिगत अपडेट तैयार है। 🔮"
                else:
                    push_msg = f"सुप्रभात {user_name} जी! आज आपके लिए {notifications_generated_today} महत्वपूर्ण अपडेट (राशिफल, त्यौहार आदि) आए हैं। 🔔"

                try:
                    send_push_to_user(profile.user, push_title, push_msg, "/?tab=notifications")
                    print(f"     🔔 स्मार्ट पुश भेजा गया ({notifications_generated_today} नए अलर्ट्स)।")
                    sent_users_count += 1
                except Exception as e:
                    print(f"     ⚠️ पुश नोटिफिकेशन भेजने में त्रुटि: {e}")

        time.sleep(0.5) # Gemini API को Rate-Limit से बचाने के लिए

    print("\n" + "━" * 60)
    print(f"  🏁 मास्टर इंजन सफलतापूर्वक पूरा हुआ! कुल {sent_users_count} यूज़र्स को आज नोटिफिकेशन भेजे गए।")
    print("━" * 60 + "\n")

if __name__ == "__main__":
    run_master_engine()
