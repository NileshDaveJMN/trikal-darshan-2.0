"""
core/views/trikal_api_views.py
Render bot ke liye secure API endpoints.

Endpoints:
  POST /api/bot/save-chat-id/      — Telegram chat_id save karo
  GET  /api/bot/pending-horoscope/ — Pending users list
  POST /api/bot/save-horoscope/    — Horoscope save karo
  GET  /api/bot/send-horoscope/    — cron-job.org se daily horoscope trigger
"""
import json, os, datetime, threading
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from core.models import UserProfile, SavedKundali

# .env load (PythonAnywhere ke liye)
_env = Path(__file__).parent.parent.parent / '.env'
if _env.exists():
    for _line in _env.read_text(encoding='utf-8').splitlines():
        _line = _line.strip()
        if _line and '=' in _line and not _line.startswith('#'):
            _k, _v = _line.split('=', 1)
            os.environ.setdefault(_k.strip(), _v.strip())

BOT_SECRET = os.getenv("BOT_API_SECRET", "trikal-secret-2026")

def _auth(request):
    """Secret key check"""
    return request.headers.get("X-Bot-Secret", "") == BOT_SECRET


# ─────────────────────────────────────────────
#  API 1 — Chat ID Save
#  POST /api/bot/save-chat-id/
# ─────────────────────────────────────────────
@csrf_exempt
def api_save_chat_id(request):
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)
    if not _auth(request):
        return JsonResponse({"ok": False, "error": "Unauthorized"}, status=401)
    try:
        d = json.loads(request.body)
        username = d.get("username", "").strip()
        chat_id  = str(d.get("chat_id", "")).strip()
        user = User.objects.get(username=username)
        user.userprofile.telegram_chat_id = chat_id
        user.userprofile.save(update_fields=["telegram_chat_id"])
        return JsonResponse({"ok": True, "display_name": user.first_name or user.username})
    except User.DoesNotExist:
        return JsonResponse({"ok": False, "error": "User nahi mila"}, status=404)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


# ─────────────────────────────────────────────
#  API 2 — Pending Horoscope Users
#  GET /api/bot/pending-horoscope/
# ─────────────────────────────────────────────
def api_pending_horoscope(request):
    if not _auth(request):
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
        if p.horoscope_date == today:
            continue
        k = SavedKundali.objects.filter(user=p.user).order_by("created_at").first()
        if not k:
            continue
        pending.append({
            "username":          p.user.username,
            "display_name":      p.user.first_name or p.user.username,
            "chat_id":           p.telegram_chat_id,
            "profession":        p.profession or "",
            "primary_focus":     p.primary_focus or "",
            "current_challenge": p.current_challenge or "",
            "relationship_status": p.relationship_status or "",
            "finance_focus":     p.finance_focus or "",
            "kundali": {
                "name":   k.name,
                "day":    k.day,
                "month":  k.month,
                "year":   k.year,
                "hour":   k.hour,
                "minute": k.minute,
                "second": getattr(k, "second", 0),
                "lat":    k.lat,
                "lon":    k.lon,
                "city":   k.city,
            }
        })
    return JsonResponse({"ok": True, "today": str(today), "count": len(pending), "users": pending})


# ─────────────────────────────────────────────
#  API 3 — Horoscope Save
#  POST /api/bot/save-horoscope/
# ─────────────────────────────────────────────
@csrf_exempt
def api_save_horoscope(request):
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)
    if not _auth(request):
        return JsonResponse({"ok": False, "error": "Unauthorized"}, status=401)
    try:
        d = json.loads(request.body)
        user = User.objects.get(username=d.get("username", "").strip())
        p = user.userprofile
        p.daily_horoscope_text = d.get("horoscope_text", "")
        p.horoscope_date = datetime.date.today()
        p.save(update_fields=["daily_horoscope_text", "horoscope_date"])
        return JsonResponse({"ok": True})
    except User.DoesNotExist:
        return JsonResponse({"ok": False, "error": "User nahi mila"}, status=404)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


# ─────────────────────────────────────────────
#  API 4 — Daily Horoscope Trigger
#  GET /api/bot/send-horoscope/
#  cron-job.org se call hoga subah 7 baje
# ─────────────────────────────────────────────
@csrf_exempt
def api_send_daily_horoscope(request):
    if not _auth(request):
        return JsonResponse({"ok": False}, status=401)

    def run_horoscope():
        try:
            import sys, os
            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if root not in sys.path:
                sys.path.insert(0, root)
            from trikal_bot import send_daily_horoscopes
            send_daily_horoscopes()
        except Exception as e:
            print(f"Horoscope error: {e}")

    threading.Thread(target=run_horoscope, daemon=True).start()
    return JsonResponse({"ok": True})
