import os
import sys
import datetime
import time
import traceback
import threading
import pytz

# ── 1. Django Setup ──
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trikal_portal.settings')
import django
django.setup()

# 🆕 EngineRun import — roz ka run record
from core.models import UserProfile, SavedKundali, PushSubscription, EngineRun
from core.views.push_views import send_push_to_user
from django.utils import timezone as dj_tz

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

# ── 3. 🆕 Engine Lock (same-process double-thread guard) ──
_engine_lock = threading.Lock()


def _keepalive_loop(stop_event):
    """🆕 Render free tier mid-run sleep se bachne ke liye har 5 min self-ping.
    RENDER_EXTERNAL_URL Render khud set karta hai. Paid tier / cron-job pe
    move karoge to ye function delete kar dena."""
    import requests
    url = os.getenv("RENDER_EXTERNAL_URL")
    if not url:
        return
    while not stop_event.wait(300):
        try:
            requests.get(url, timeout=10)
        except Exception:
            pass


def run_master_engine():
    # 🆕 Guard 1: isi process mein engine pehle se chal rahi hai to skip
    if not _engine_lock.acquire(blocking=False):
        print("⛔ Engine isi process mein pehle se chal rahi hai — skip.")
        return
    try:
        # 🆕 Guard 2 (DB-based): pichli run abhi tak RUNNING hai to skip.
        # Purani (stale) RUNNING ko INTERRUPTED mark karo — matlab process beech mein mara tha.
        recent = EngineRun.objects.filter(status="RUNNING").order_by("-started_at").first()
        if recent:
            age = (dj_tz.now() - recent.started_at).total_seconds()
            if age < 7200:  # 2 ghante
                print(f"⛔ Pichli run {int(age // 60)} min pehle start hui, abhi tak RUNNING — skip.")
                return
            recent.status = "INTERRUPTED"
            recent.save(update_fields=["status"])

        _run_engine()
    finally:
        _engine_lock.release()


def _run_engine():
    print("\n" + "━" * 60)
    print("  🚀 Trikal Darshan - Master AI Engine (v2.0)")
    print("━" * 60)

    IST = pytz.timezone("Asia/Kolkata")
    today = datetime.datetime.now(IST).date()

    # 🆕 Is run ka record — start pe RUNNING, end pe final status
    run = EngineRun.objects.create(date=today, status="RUNNING")

    errors = []
    users_ok = users_failed = users_no_kundali = sent_users_count = 0

    # 🆕 Keep-alive thread — engine chalne tak service jagti rahegi
    stop_keepalive = threading.Event()
    threading.Thread(target=_keepalive_loop, args=(stop_keepalive,), daemon=True).start()

    # ── STEP 1: Global Calculations (🆕 har step ab guarded) ──
    print("\n  🌍 1. ग्लोबल डेटा तैयार किया जा रहा है...")

    # a. 12 rashiyon ka rashifal
    try:
        pre_generate_12_rashifal()
    except Exception as e:
        errors.append(f"STEP1a pre_generate_12_rashifal: {repr(e)[:300]}")
        print(f"  ❌ राशिफल जनरेशन फेल: {e}")

    # b. Aaj ka panchang aur tyohar
    today_festivals = []
    try:
        panchang = get_today_panchang()
        today_festivals = get_today_festivals(panchang) if panchang else []
    except Exception as e:
        errors.append(f"STEP1b panchang: {repr(e)[:300]}")
        print(f"  ❌ पंचांग फेल: {e}")

    if today_festivals:
        print(f"  🎉 आज के त्यौहार ({len(today_festivals)}):")
        for f in today_festivals:
            print(f"     - {f.get('emoji', '')} {f['name']}")
    else:
        print("  ℹ️ आज कोई विशेष पर्व नहीं है।")

    # c. Aaj ka gochar — 🆕 CRITICAL GUARD:
    #    Pehle yahan crash hoti to POORI engine mar jati thi.
    #    Ab fail ho to personalized rashifal skip, par tyohar/dasha modules chalte hain.
    tz = pytz.timezone("Asia/Kolkata")
    now = datetime.datetime.now(tz)
    today_jd = _dt_to_jd(now, "Asia/Kolkata")
    today_transit = None
    try:
        today_transit = calculate_transit_positions(today_jd)
    except Exception as e:
        errors.append(f"STEP1c calculate_transit_positions: {repr(e)[:300]}")
        print(f"  ❌ गोचर गणना फेल — आज व्यक्तिगत राशिफल छोड़ रहे हैं: {e}")

    # d. Gochar parivartan detect karo
    gochar_changes = []
    try:
        today_gochar = get_current_gochar(today_jd)
        yesterday_gochar = get_yesterday_gochar(today_jd)
        gochar_changes = detect_gochar_changes(yesterday_gochar, today_gochar)
    except Exception as e:
        errors.append(f"STEP1d gochar change detect: {repr(e)[:300]}")
        print(f"  ❌ गोचर परिवर्तन डिटेक्शन फेल: {e}")

    if gochar_changes:
        print(f"\n  🪐 आज {len(gochar_changes)} ग्रह ने राशि बदली:")
        for c in gochar_changes:
            print(f"     {c['emoji']} {c['graha']}: {c['old_rashi']} → {c['new_rashi']}")
    else:
        print("  ℹ️ आज कोई गोचर परिवर्तन नहीं है।")

    # ── STEP 2: User Loop ──
    # 🆕 inactive users skip (pehle .all() tha)
    profiles = UserProfile.objects.select_related("user").filter(user__is_active=True)
    total_users = profiles.count()
    run.total_users = total_users
    run.save(update_fields=["total_users"])
    print(f"\n  👥 2. कुल यूज़र्स: {total_users}")

    for profile in profiles:
        user_name = profile.user.first_name or profile.user.username

        # 🆕 PER-USER GUARD — ek user fail ho to uske baad wale users safe rahenge
        try:
            # ⚠️ DECISION: abhi sabse PURANI kundali use ho rahi hai (order_by asc).
            # Latest chahiye to order_by("-created_at").first() karo — niche dekho.
            kundali = SavedKundali.objects.filter(user=profile.user).order_by("created_at").first()

            if not kundali:
                users_no_kundali += 1
                continue

            print(f"\n  👤 प्रोसेसिंग: {user_name} ({profile.user.username})")

            natal_pos, natal_jd = calculate_natal_positions(kundali)
            lagna_idx = calculate_lagna(natal_jd, kundali.lat, kundali.lon)
            dasha = build_dasha_info(kundali)

            notifications_generated_today = 0

            # A. Dainik Rashifal — 🆕 sirf tab jab transit calculate hui ho
            if today_transit is not None:
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

            users_ok += 1

        except Exception as e:
            # 🆕 Ye tha asli bug — iske bina ek user ki exception poori engine maar deti thi
            users_failed += 1
            err = f"{profile.user.username}: {repr(e)[:300]}"
            errors.append(err)
            print(f"  ❌ यूज़र फेल (आगे चलते रहेंगे): {err}")
            traceback.print_exc()
            continue

        time.sleep(0.5)

    # ── 🆕 FINALIZE: EngineRun update + keep-alive band ──
    stop_keepalive.set()

    run.users_ok = users_ok
    run.users_failed = users_failed
    run.users_no_kundali = users_no_kundali
    run.notifications_sent = sent_users_count
    run.finished_at = datetime.datetime.now(IST)
    run.errors = "\n".join(errors)

    if errors and users_ok == 0 and total_users > 0:
        run.status = "FAILED"
    elif not errors and users_failed == 0:
        run.status = "SUCCESS"
    else:
        run.status = "PARTIAL"
    run.save()

    print("\n" + "━" * 60)
    print(f"  🏁 इंजन पूरा! Status: {run.status}")
    print(f"     यूज़र्स: {users_ok} OK / {users_failed} फेल / {users_no_kundali} बिना कुंडली")
    print(f"     पुश भेजे: {sent_users_count}")
    if errors:
        print(f"     ⚠️ {len(errors)} त्रुटियाँ — admin panel में EngineRun देखो")
    print("━" * 60 + "\n")


if __name__ == "__main__":
    # ⚠️ Local test: real users ko notifications jayenge — dhyan se!
    run_master_engine()