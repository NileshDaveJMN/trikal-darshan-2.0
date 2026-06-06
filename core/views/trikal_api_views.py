# core/views/trikal_api_views.py
import json
import os
import datetime
import threading
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from core.models import UserProfile, PushSubscription, UserNotification

# .env से secret key load करना
_env = Path(__file__).parent.parent.parent / '.env'
if _env.exists():
    for _line in _env.read_text(encoding='utf-8').splitlines():
        _line = _line.strip()
        if _line and '=' in _line and not _line.startswith('#'):
            _k, _v = _line.split('=', 1)
            os.environ.setdefault(_k.strip(), _v.strip())

BOT_SECRET = os.getenv("BOT_API_SECRET", "trikal-secret-2026")

def check_secret(request):
    secret = request.headers.get("X-Bot-Secret", "")
    return secret == BOT_SECRET

@csrf_exempt
def api_send_daily_horoscope(request):
    if not check_secret(request):
        return JsonResponse({"ok": False}, status=401)
    def run_horoscope():
        try:
            import sys, os
            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if root not in sys.path:
                sys.path.insert(0, root)
                
            # Step 1: Rashifal generate karo
            from daily_horoscope_engine import generate_daily_horoscopes
            generate_daily_horoscopes()

            # 🚀 Step 1.5: Festival Engine चलाएं (नया फिक्स)
            try:
                from festival_engine import send_festival_notifications
                send_festival_notifications()
            except Exception as fe:
                print(f"Festival engine error: {fe}")


            # 2. पुश नोटिफिकेशन भेजें
            from core.views.push_views import send_push_to_user
            profiles = UserProfile.objects.select_related("user").all()
            sent = 0
            
            for profile in profiles:
                subs = PushSubscription.objects.filter(user=profile.user, is_active=True)
                if subs.exists():
                    # लेटेस्ट नोटिफिकेशन इनबॉक्स से उठाएं
                    latest_notif = UserNotification.objects.filter(
                        user=profile.user, 
                        notification_type='DAILY'
                    ).order_by('-created_at').first()

                    if latest_notif:
                        name = profile.user.first_name or profile.user.username
                        text = latest_notif.message[:100] + "..."
                        
                        # सीधे 'सूचनाएं' टैब का लिंक भेजें
                        send_push_to_user(
                            profile.user,
                            f"🔮 {name} जी, आज का राशिफल तैयार है",
                            text,
                            "/?tab=view-notifications"
                        )
                        sent += 1
                        print(f"  📲 Push sent: {profile.user.username}")
            
            # 3. त्यौहार नोटिफिकेशन
            try:
                from festival_engine import send_festival_notifications
                send_festival_notifications()
            except Exception as e:
                print("Festival error:", e)

        except Exception as e:
            print(f"Horoscope generation error: {e}")
            import traceback; traceback.print_exc()

    # बैकग्राउंड में चलाएं ताकि वेबसाइट हैंग न हो
    threading.Thread(target=run_horoscope, daemon=True).start()
    return JsonResponse({"ok": True, "message": "Horoscope generation started!"})

# पुराने Telegram वाली APIs को आप यहाँ से हटा सकते हैं, 
# या रहने दें, उनसे कोई फर्क नहीं पड़ेगा क्योंकि अब Telegram बॉट का कोई काम नहीं है।
