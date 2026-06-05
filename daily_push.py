import os
import sys

# ── Path & Django Setup FIRST ─────────────────────────────────────────
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trikal_portal.settings')

import django
django.setup()

# ── Now import everything else ────────────────────────────────────────
# 🚀 UserNotification यहाँ इम्पोर्ट किया गया है
from core.models import UserProfile, PushSubscription, UserNotification
from core.views.push_views import send_push_to_user
from daily_horoscope_engine import generate_daily_horoscopes
from festival_engine import send_festival_notifications

# ── Step 1: Generate all horoscopes ──────────────────────────────────
generate_daily_horoscopes()

# ── Step 2: Send personal horoscope push notifications ───────────────
print("\n" + "─" * 55)
print("  📲 Personal Horoscope Notifications")
print("─" * 55)

profiles = UserProfile.objects.select_related("user").all()
sent = 0
for profile in profiles:
    subs = PushSubscription.objects.filter(user=profile.user, is_active=True)
    if subs.exists():
        # 🚀 अब ये पुराने UserProfile की जगह नए इनबॉक्स (UserNotification) से डाटा उठाएगा
        latest_notif = UserNotification.objects.filter(
            user=profile.user, 
            notification_type='DAILY'
        ).order_by('-created_at').first()

        if latest_notif:
            name = profile.user.first_name or profile.user.username
            text = latest_notif.message[:100] + "..."
            
            send_push_to_user(
                profile.user,
                f"🔮 {name} जी, आज का राशिफल तैयार है",
                text,
                "/?tab=view-notifications" # 🚀 क्लिक करने पर सीधा "सूचनाएं" टैब खुलेगा
            )
            print(f"  📲 Sent: {profile.user.username}")
            sent += 1

print(f"  ✅ Total notifications sent: {sent}")

# ── Step 3: Festival notifications ───────────────────────────────────
send_festival_notifications()
