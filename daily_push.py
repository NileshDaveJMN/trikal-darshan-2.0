import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trikal_portal.settings')
django.setup()

from core.models import UserProfile, PushSubscription
from core.views.push_views import send_push_to_user
from daily_horoscope_engine import generate_daily_horoscopes

# Pehle sab ka rashifal generate karo
generate_daily_horoscopes()

# Phir push notification bhejo
profiles = UserProfile.objects.select_related("user").all()
for profile in profiles:
    subs = PushSubscription.objects.filter(user=profile.user, is_active=True)
    if subs.exists() and profile.daily_horoscope_text:
        name = profile.user.first_name or profile.user.username
        text = profile.daily_horoscope_text[:100] + "..."
        send_push_to_user(profile.user, f"🔮 {name} जी, आज का राशिफल", text, "/")
        print(f"  📲 Notification sent: {profile.user.username}")