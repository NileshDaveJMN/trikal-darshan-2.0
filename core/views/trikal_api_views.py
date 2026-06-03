"""
core/views/trikal_api_views.py

Render par chal rahe bot ke liye API endpoints.
Secret key se secure hai — koi bhi call nahi kar sakta.
"""

import json
import os
import datetime
import threading
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from core.models import UserProfile, SavedKundali

# .env se secret key load karo
_env = Path(__file__).parent.parent.parent / '.env'
if _env.exists():
    for _line in _env.read_text(encoding='utf-8').splitlines():
        _line = _line.strip()
        if _line and '=' in _line and not _line.startswith('#'):
            _k, _v = _line.split('=', 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# Render bot ka secret — .env mein add karo: BOT_API_SECRET=koi_bhi_random_string
BOT_SECRET = os.getenv("BOT_API_SECRET", "trikal-secret-2026")


def check_secret(request):
    """Request mein secret check karo"""
    secret = request.headers.get("X-Bot-Secret", "")
    return secret == BOT_SECRET


# ─────────────────────────────────────────────
#  API 1 — Chat ID Save karo
#  POST /api/bot/save-chat-id/
# ─────────────────────────────────────────────
@csrf_exempt
def api_save_chat_id(request):
    """
    Render bot se chat_id aata hai — DB mein save karo.
    Body: {"username": "Newnilesh", "chat_id": "8943971061"}
    """
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST only"}, status=405)

    if not check_secret(request):
        return JsonResponse({"ok": False, "error": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body.decode("utf-8"))
        username = data.get("username", "").strip()
        chat_id  = str(data.get("chat_id", "")).strip()

        if not username or not chat_id:
            return JsonResponse({"ok": False, "error": "username aur chat_id dono chahiye"})

        user = User.objects.get(username=username)
        profile = user.userprofile
        profile.telegram_chat_id = chat_id
        profile.save(update_fields=["telegram_chat_id"])

        print(f"✅ API: {username} → chat_id {chat_id} saved")
        return JsonResponse({
            "ok": True,
            "message": f"{username} ka chat_id save ho gaya",
            "display_name": user.first_name or user.username
        })

    except User.DoesNotExist:
        return JsonResponse({"ok": False, "error": f"User nahi mila"}, status=404)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


# ─────────────────────────────────────────────
#  API 2 — Pending Horoscope Users list
#  GET /api/bot/pending-horoscope/
# ─────────────────────────────────────────────
def api_pending_horoscope(request):
    """
    Jin users ka aaj ka horoscope nahi bheja — unki list do.
    Render bot ye call karta hai subah.
    """
    if not check_secret(request):
        return JsonResponse({"ok": False, "error": "Unauthorized"}, status=401)

    today = datetime.date.today()

    profiles = (
        UserProfile.objects
        .select_related("user")
        .exclude(telegram_chat_id__isnull=True)
        .exclude(telegram_chat_id__exact="")
    )

    pending = []
    for p in profiles:
        if p.horoscope_date != today:
            # Primary kundali
            kundali = (
                SavedKundali.objects
                .filter(user=p.user)
                .order_by("created_at")
                .first()
            )
            if not kundali:
                continue

            pending.append({
                "username":         p.user.username,
                "display_name":     p.user.first_name or p.user.username,
                "chat_id":          p.telegram_chat_id,
                "telegram_chat_id": p.telegram_chat_id,
                "profession":       p.profession or "",
                "primary_focus":    p.primary_focus or "",
                "current_challenge": p.current_challenge or "",
                "relationship_status": p.relationship_status or "",
                "finance_focus":    p.finance_focus or "",
                "kundali": {
                    "name":   kundali.name,
                    "day":    kundali.day,
                    "month":  kundali.month,
                    "year":   kundali.year,
                    "hour":   kundali.hour,
                    "minute": kundali.minute,
                    "second": getattr(kundali, "second", 0),
                    "lat":    kundali.lat,
                    "lon":    kundali.lon,
                    "city":   kundali.city,
                }
            })

    return JsonResponse({
        "ok": True,
        "today": str(today),
        "count": len(pending),
        "users": pending
    })


# ─────────────────────────────────────────────
#  API 3 — Horoscope Save karo (bhejne ke baad)
#  POST /api/bot/save-horoscope/
# ─────────────────────────────────────────────
@csrf_exempt
def api_save_horoscope(request):
    """
    Render bot ne Telegram par horoscope bhej diya —
    ab DB mein save karo.
    Body: {"username": "Newnilesh", "horoscope_text": "..."}
    """
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST only"}, status=405)

    if not check_secret(request):
        return JsonResponse({"ok": False, "error": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body.decode("utf-8"))
        username = data.get("username", "").strip()
        text     = data.get("horoscope_text", "").strip()

        user    = User.objects.get(username=username)
        profile = user.userprofile
        profile.daily_horoscope_text = text
        profile.horoscope_date       = datetime.date.today()
        profile.save(update_fields=["daily_horoscope_text", "horoscope_date"])

        return JsonResponse({"ok": True, "message": f"{username} ka horoscope save ho gaya"})

    except User.DoesNotExist:
        return JsonResponse({"ok": False, "error": "User nahi mila"}, status=404)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

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
            # Step 2: Push notifications bhejo
            from core.models import UserProfile, PushSubscription
            from core.views.push_views import send_push_to_user
            profiles = UserProfile.objects.select_related("user").all()
            for profile in profiles:
                subs = PushSubscription.objects.filter(user=profile.user, is_active=True)
                if subs.exists() and profile.daily_horoscope_text:
                    name = profile.user.first_name or profile.user.username
                    text = profile.daily_horoscope_text[:100] + "..."
                    send_push_to_user(profile.user, f"🔮 {name} जी, आज का राशिफल", text, "/")
                    print(f"  📲 Push sent: {profile.user.username}")
        except Exception as e:
            print(f"Horoscope error: {e}")
            import traceback; traceback.print_exc()
    import threading
    threading.Thread(target=run_horoscope, daemon=True).start()
    return JsonResponse({"ok": True, "message": "Horoscope generation started!"})
