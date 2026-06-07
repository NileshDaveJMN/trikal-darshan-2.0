# core/views/trikal_api_views.py
import os
import threading
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

_env = Path(__file__).parent.parent.parent / '.env'
if _env.exists():
    for _line in _env.read_text(encoding='utf-8').splitlines():
        _line = _line.strip()
        if _line and '=' in _line and not _line.startswith('#'):
            _k, _v = _line.split('=', 1)
            os.environ.setdefault(_k.strip(), _v.strip())

BOT_SECRET = os.getenv("BOT_API_SECRET", "trikal-secret-2026")

def check_secret(request):
    return request.headers.get("X-Bot-Secret", "") == BOT_SECRET

@csrf_exempt
def api_send_daily_horoscope(request):
    if not check_secret(request):
        return JsonResponse({"ok": False}, status=401)

    def run():
        try:
            import sys
            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if root not in sys.path:
                sys.path.insert(0, root)
            from master_cron import run_master_engine
            run_master_engine()
        except Exception as e:
            import traceback
            print(f"Engine error: {e}")
            traceback.print_exc()

    threading.Thread(target=run, daemon=True).start()
    return JsonResponse({"ok": True, "message": "Engine started!"})