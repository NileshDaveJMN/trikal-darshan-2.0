# core/views/trikal_api_views.py
import json
import os
import datetime
import threading
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from core.models import UserProfile

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

            # ✅ नया Master Engine — होरोस्कोप + फेस्टिवल + पुश सब एक जगह
            from master_cron import run_master_engine
            run_master_engine()

        except Exception as e:
            print(f"Master engine error: {e}")
            import traceback; traceback.print_exc()

    # बैकग्राउंड में चलाएं ताकि वेबसाइट हैंग न हो
    threading.Thread(target=run_horoscope, daemon=True).start()
    return JsonResponse({"ok": True, "message": "Master engine started!"})