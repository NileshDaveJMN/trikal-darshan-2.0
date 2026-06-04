import os
import sys

# ── Path & Django Setup FIRST ─────────────────────────────────────────
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trikal_portal.settings')

import django
django.setup()

# ── Now import everything else ────────────────────────────────────────
from core.models import UserProfile, PushSubscription
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
    if subs.exists() and profile.daily_horoscope_text:
        name = profile.user.first_name or profile.user.username
        text = profile.daily_horoscope_text[:100] + "..."
        send_push_to_user(
            profile.user,
            f"🔮 {name} जी, आज का राशिफल तैयार है",
            text,
            "/"
        )
        print(f"  📲 Sent: {profile.user.username}")
        sent += 1

print(f"  ✅ Total notifications sent: {sent}")

# ── Step 3: Festival notifications ───────────────────────────────────
send_festival_notifications()