#!/usr/bin/env python
# =====================================================
# daily_push.py — root folder mein rakho
# Render Cron Job se roz subah 6 AM call hoga
# =====================================================

import os
import sys
import django

# Django setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trikal_portal.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import UserProfile, SavedKundali, PushSubscription
from core.views.push_views import send_push_to_user

# Horoscope engine — aapka existing
try:
    from daily_horoscope_engine import get_daily_horoscope
    HOROSCOPE_AVAILABLE = True
except ImportError:
    HOROSCOPE_AVAILABLE = False
    print("[DAILY PUSH] Warning: daily_horoscope_engine not found")


def get_horoscope_for_user(user):
    """User ki pehli kundali se horoscope banao"""
    try:
        if not HOROSCOPE_AVAILABLE:
            return "🌅 आज का दिन शुभ हो! अपनी कुंडली देखें।"

        kundali = SavedKundali.objects.filter(user=user).first()
        if not kundali:
            return "🌅 आज का दिन शुभ हो! कुंडली बनाएं।"

        # Aapke existing engine ka use karo
        result = get_daily_horoscope(
            day=kundali.day,
            month=kundali.month,
            year=kundali.year,
            hour=kundali.hour,
            minute=kundali.minute,
            lat=kundali.lat,
            lon=kundali.lon,
        )
        # Result string ya dict ho sakta hai
        if isinstance(result, dict):
            return result.get("text", "आज का दिन शुभ हो!")
        return str(result)[:200]  # Notification mein zyada text nahi aata

    except Exception as e:
        print(f"[DAILY PUSH] Horoscope error for {user.username}: {e}")
        return "🌅 आज का राशिफल देखें — त्रिकाल दर्शन पर।"


def send_daily_horoscope():
    """Sab subscribed users ko roz ka horoscope bhejo"""
    print("[DAILY PUSH] Starting daily horoscope push...")

    # Sirf unhe bhejo jinke paas active push subscription hai
    active_user_ids = PushSubscription.objects.filter(
        is_active=True
    ).values_list('user_id', flat=True).distinct()

    users = User.objects.filter(id__in=active_user_ids)
    print(f"[DAILY PUSH] Total users to notify: {users.count()}")

    total_sent = 0
    for user in users:
        horoscope_text = get_horoscope_for_user(user)
        display_name   = user.first_name or user.username

        sent = send_push_to_user(
            user=user,
            title=f"🔮 {display_name} जी, आज का राशिफल",
            body=horoscope_text,
            url="/",
        )
        total_sent += sent
        print(f"  ✅ {user.username} → {sent} device(s)")

    print(f"[DAILY PUSH] Done! Total notifications sent: {total_sent}")


if __name__ == "__main__":
    send_daily_horoscope()
