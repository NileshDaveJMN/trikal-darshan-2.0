# core/views/panchang_views.py
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from engines.panchang_engine import get_panchang_data
from engines.festival_alerts import get_today_festivals


def panchang(request):
    """
    Panchang view — ab user ki default location DB se load hoti hai.
    Agar user ne location set ki hai to wahi use hogi.
    """
    date_str = request.GET.get('date')

    # 1. Default location — pehle URL params, phir DB, phir Delhi
    default_lat  = '28.5839'
    default_lon  = '77.2090'
    default_city = 'नई दिल्ली'

    # Login user ki saved location use karo
    if request.user.is_authenticated:
        try:
            profile = request.user.userprofile
            if profile.default_lat and profile.default_lon:
                default_lat  = str(profile.default_lat)
                default_lon  = str(profile.default_lon)
                default_city = profile.default_city or default_city
        except Exception:
            pass

    # URL params override karte hain (user ne manually change ki)
    # ✅ Empty string check: agar lat/lon URL mein hai par empty hai to default use karo
    user_lat    = request.GET.get('lat', '').strip() or default_lat
    user_lon    = request.GET.get('lon', '').strip() or default_lon
    current_city = request.GET.get('city', '').strip() or default_city

    # 2. Date
    if date_str:
        target_dt = datetime.strptime(date_str, "%Y-%m-%d")
        target_dt = target_dt.replace(hour=12, minute=0, second=0)
    else:
        target_dt = datetime.now()

    # 3. Panchang data
    # ✅ Safety: float() crash na ho agar koi bhi value invalid ho
    try:
        lat_f = float(user_lat)
        lon_f = float(user_lon)
    except (ValueError, TypeError):
        lat_f = float(default_lat)
        lon_f = float(default_lon)
    p_data = get_panchang_data(target_dt, not date_str, lat_f, lon_f)
    today_festivals = []
    if p_data:
        today_festivals = get_today_festivals(p_data)

    if p_data:
        p_data['current_city'] = current_city
        p_data['lat']          = str(lat_f)   # ✅ template hidden input ko sahi lat mile
        p_data['lon']          = str(lon_f)   # ✅ template hidden input ko sahi lon mile

    current_date_value = target_dt.strftime("%Y-%m-%d")

    # 4. Kya user ki location saved hai?
    location_saved = False
    if request.user.is_authenticated:
        try:
            profile = request.user.userprofile
            location_saved = bool(profile.default_lat and profile.default_lon)
        except Exception:
            pass

    return render(request, 'panchang.html', {
        'p_data':             p_data,
        'today_festivals': today_festivals,
        'current_date_value': current_date_value,
        'current_lat':        user_lat,
        'current_lon':        user_lon,
        'current_city':       current_city,
        'location_saved':     location_saved,
    })


@csrf_exempt
def save_default_location(request):
    """
    POST /api/save-location/
    User ki default location save karo.
    Body: {"lat": 23.02, "lon": 72.57, "city": "Ahmedabad"}
    """
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST only"}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "error": "Login required"}, status=401)

    try:
        data = json.loads(request.body.decode("utf-8"))
        lat  = float(data.get("lat", 0))
        lon  = float(data.get("lon", 0))
        city = data.get("city", "").strip()

        if not lat or not lon:
            return JsonResponse({"ok": False, "error": "lat/lon required"})

        profile = request.user.userprofile
        profile.default_lat  = lat
        profile.default_lon  = lon
        profile.default_city = city
        profile.save(update_fields=["default_lat", "default_lon", "default_city"])

        return JsonResponse({
            "ok":   True,
            "city": city,
            "lat":  lat,
            "lon":  lon,
            "message": f"'{city}' आपकी डिफ़ॉल्ट लोकेशन सेट हो गई! ✅"
        })

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@csrf_exempt
def clear_default_location(request):
    """
    POST /api/clear-location/
    User ki default location clear karo.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "error": "Login required"}, status=401)

    try:
        profile = request.user.userprofile
        profile.default_lat  = None
        profile.default_lon  = None
        profile.default_city = None
        profile.save(update_fields=["default_lat", "default_lon", "default_city"])
        return JsonResponse({"ok": True, "message": "Location clear ho gayi"})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
