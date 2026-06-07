import os
import sys
import datetime
import time
import pytz
from pathlib import Path

# ── 1. Django Setup ──
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trikal_portal.settings')
import django
django.setup()

from core.models import UserProfile, SavedKundali, PushSubscription
from core.views.push_views import send_push_to_user

# ── 2. Engines Import ──
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
from engines.gochar_alerts import (
    get_current_gochar,
    get_yesterday_gochar,
    detect_gochar_changes,
    process_user_gochar
)
from engines.dasha_alerts import process_user_dasha

def run_master_engine():
    print("\n" + "━" * 60)
    print("  🚀 Trikal Darshan - Master AI Engine (v1.2)")
    print("━" * 60)

    # ── STEP 1: Global Calculations ──
    print("\n  🌍 1. ग्लोबल डेटा तैयार किया जा रहा है...")

    # a. 12 rashiyon ka rashifal
    pre_generate_12_rashifal()

    # b. Aaj ka panchang aur tyohar
    panchang = get_today_panchang()
    today_festivals = get_today_festivals(panchang) if panchang else []

    if today_festivals:
        print(f"  🎉 आज के त्यौहार ({len(today_festivals)}):")
        for f in today_festivals:
            print(f"     - {f.get('emoji', '')} {f['name']}")
    else:
        print("  ℹ️ आज कोई विशेष पर्व नहीं है।")

    # c. Aaj ka gochar
    tz = pytz.timezone("Asia/Kolkata")
    now = datetime.datetime.now(tz)
    today_jd = _dt_to_jd(now, "Asia/Kolkata")
    today_transit = calculate_transit_positions(today_jd)

    # d. Gochar parivartan detect karo
    today_gochar     = get_current_gochar(today_jd)
    yesterday_gochar = get_yesterday_gochar(today_jd)
    gochar_changes   = detect_gochar_changes(yesterday_gochar, today_gochar)

    if gochar_changes:
        print(f"\n  🪐 आज {len(gochar_changes)} ग्रह ने रashi बदली:")
        for c in gochar_changes:
            print(f"     {c['emoji']} {c['graha']}: {c['old_rashi']} → {c['new_rashi']}")
    else:
        print("  ℹ️ आज कोई गोचर परिवर्तन नहीं है।")

    profiles = UserProfile.objects.select_related("user").all()
    print(f"\n  👥 2. कुल यूज़र्स: {profiles.count()}")

    sent_users_count = 0

    # ── STEP 2: User Loop ──
    for profile in profiles:
        user_name = profile.user.first_name or profile.user.username
        kundali = SavedKundali.objects.filter(user=profile.user).order_by("created_at").first()

        if not kundali:
            continue

        print(f"\n  👤 प्रोसेसिंग: {user_name} ({profile.user.username})")

        natal_pos, natal_jd = calculate_natal_positions(kundali)
        lagna_idx = calculate_lagna(natal_jd, kundali.lat, kundali.lon)
        dasha = build_dasha_info(kundali)

        notifications_generated_today = 0

        # ── STEP 3: Sabhi Modules ──

        # A. Dainik Rashifal
        is_horoscope_new = process_user_horoscope(profile, kundali, natal_pos, lagna_idx, dasha, today_transit)
        if is_horoscope_new:
            notifications_generated_today += 1

        # B. Tyohar Alert
        if today_festivals:
            main_festival = today_festivals[0]
            is_festival_new = process_user_festival(profile, kundali, natal_pos, lagna_idx, dasha, main_festival)
            if is_festival_new:
                notifications_generated_today += 1

        # C. Gochar Parivartan Alert
        if gochar_changes:
            gochar_new = process_user_gochar(profile, kundali, natal_pos, lagna_idx, dasha, gochar_changes)
            notifications_generated_today += gochar_new

        # D. Dasha Parivartan Alert
        dasha_new = process_user_dasha(profile, kundali, natal_pos, lagna_idx)
        notifications_generated_today += dasha_new

        # ── STEP 4: Smart Push Notification ──
        if notifications_generated_today > 0:
            subs = PushSubscription.objects.filter(user=profile.user, is_active=True)
            if subs.exists():
                push_title = "✨ त्रिकाल दर्शन अपडेट"
                if notifications_generated_today == 1:
                    push_msg = f"सुप्रभात {user_name} जी! आपका आज का व्यक्तिगत अपडेट तैयार है। 🔮"
                else:
                    push_msg = f"सुप्रभात {user_name} जी! आज आपके लिए {notifications_generated_today} महत्वपूर्ण अपडेट आए हैं। 🔔"

                try:
                    send_push_to_user(profile.user, push_title, push_msg, "/?tab=notifications")
                    print(f"     🔔 पुश भेजा ({notifications_generated_today} अलर्ट्स)।")
                    sent_users_count += 1
                except Exception as e:
                    print(f"     ⚠️ पुश त्रुटि: {e}")

        time.sleep(0.5)

    print("\n" + "━" * 60)
    print(f"  🏁 इंजन पूरा! कुल {sent_users_count} यूज़र्स को नोटिफिकेशन भेजे।")
    print("━" * 60 + "\n")

if __name__ == "__main__":
    run_master_engine()
