from django.http import JsonResponse
import os
import json
from django.shortcuts import render, redirect

from datetime import datetime
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from .models import UserProfile, SavedKundali, Lead, TabSettings
from django.utils import timezone
from datetime import timedelta

# आपके इंजनों को इम्पोर्ट कर रहे हैं
from engines.kundali_engine import get_kundali_data
from engines.panchang_engine import get_panchang_data

MONTHS = ["जनवरी", "फरवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]
BASE_DIR = settings.BASE_DIR
MSG_FILE = os.path.join(BASE_DIR, 'messages.json')
ANALYTICS_FILE = os.path.join(BASE_DIR, 'analytics.json')

# --- Helper Functions ---
def load_messages():
    if os.path.exists(MSG_FILE):
        with open(MSG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_message(msg):
    msgs = load_messages()
    msgs.insert(0, msg)
    with open(MSG_FILE, 'w', encoding='utf-8') as f:
        json.dump(msgs, f, indent=4, ensure_ascii=False)

def update_analytics(page_type):
    stats = {"total": 0, "kundali_total": 0, "panchang_total": 0}
    if os.path.exists(ANALYTICS_FILE):
        with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f:
            stats = json.load(f)
    
    stats["total"] += 1
    if page_type == 'kundali':
        stats["kundali_total"] += 1
    elif page_type == 'panchang':
        stats["panchang_total"] += 1
        
    with open(ANALYTICS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=4)

# --- Main View ---
def index(request):
    # 1. डेटाबेस से फीचर्स की सेटिंग्स उठाएं (ID का झंझट खत्म)
    tab_settings = TabSettings.objects.first()
    if not tab_settings:
        tab_settings = TabSettings.objects.create()

    # GET रिक्वेस्ट के लिए एनालिटिक्स अपडेट
    if request.method == 'GET':
        update_analytics('kundali')
        
    res = None
    saved_kundalis = []
    
    # यूजर की सेव की गई कुंडलियां
    if request.user.is_authenticated:
        saved_kundalis = SavedKundali.objects.filter(user=request.user).order_by('-id')[:10]

    if request.method == 'POST':
        def s_int(v): return int(v) if v and str(v).strip() else 0
        def s_float(v): return float(v) if v and str(v).strip() else 0.0

        # फॉर्म डेटा
        n = request.POST.get('name')
        g = request.POST.get('gender')
        d = s_int(request.POST.get('dd'))
        m = s_int(request.POST.get('mm'))
        y = s_int(request.POST.get('yyyy'))
        h = s_int(request.POST.get('hh'))
        min_m = s_int(request.POST.get('min'))
        s = s_int(request.POST.get('sec'))
        c = request.POST.get('city_name')
        lat = s_float(request.POST.get('lat'))
        lon = s_float(request.POST.get('lon'))

        action = request.POST.get('action')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # AJAX रिक्वेस्ट (AI Analysis के लिए)
        if is_ajax and action == 'get_ai':
            topics_raw = request.POST.get('topics', '') 
            topics_list = [t.strip() for t in topics_raw.split(',') if t.strip()]
            custom_q = request.POST.get('custom_question', '')
            
            res_ai = get_kundali_data(n, g, d, m, y, h, min_m, s, c, lat, lon, 
                                      need_ai=True, 
                                      selected_topics=topics_list, 
                                      custom_question=custom_q)
            
            if res_ai and res_ai.get('predictions'):
                return JsonResponse({'status': 'success', 'ai_data': res_ai['predictions']})
            return JsonResponse({'status': 'error', 'message': 'AI इंजन ने डेटा जनरेट नहीं किया।'})

        # नॉर्मल कुंडली कैलकुलेशन
        res = get_kundali_data(n, g, d, m, y, h, min_m, s, c, lat, lon, need_ai=False)
        
        # कुंडली सेव करना
        if res and request.user.is_authenticated and action == 'calc':
            SavedKundali.objects.get_or_create(
                user=request.user, name=n, gender=g, day=d, month=m, year=y,
                hour=h, minute=min_m, second=s, city=c, lat=lat, lon=lon
            )
            saved_kundalis = SavedKundali.objects.filter(user=request.user).order_by('-id')[:10]

    # ड्रॉपडाउन ऑप्शंस
    month_choices = [{'val': i+1, 'name': month} for i, month in enumerate(MONTHS)]
    
    context = {
        'tabs': tab_settings,  # एडमिन पैनल का कंट्रोल
        'res': res, 
        'days': range(1, 32), 
        'month_choices': month_choices,
        'years': range(1940, 2027), 
        'hours': range(0, 24),
        'minutes': range(0, 60), 
        'seconds': range(0, 60),
        'saved_kundalis': saved_kundalis
    }
    return render(request, 'home.html', context)

# --- Other Views ---
def api_get_ai_analysis(request):
    if request.method == 'POST':
        try:
            def s_int(v): return int(v) if v and str(v).strip() else 0
            def s_float(v): return float(v) if v and str(v).strip() else 0.0

            selected_topics = request.POST.getlist('topics')
            custom_question = request.POST.get('custom_question', '').strip()
            
            res = get_kundali_data(
                request.POST.get('name'), request.POST.get('gender'), 
                s_int(request.POST.get('dd')), s_int(request.POST.get('mm')), s_int(request.POST.get('yyyy')), 
                s_int(request.POST.get('hh')), s_int(request.POST.get('min')), s_int(request.POST.get('sec')),
                request.POST.get('city_name'), s_float(request.POST.get('lat')), s_float(request.POST.get('lon')),
                need_ai=True, selected_topics=selected_topics, custom_question=custom_question
            )
            
            if res and res.get('predictions'):
                return JsonResponse({"status": "success", "predictions": res['predictions']})
            return JsonResponse({"status": "error", "message": "AI सर्वर व्यस्त है।"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid Request"})

def panchang(request):
    date_str = request.GET.get('date')
    target_dt = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()
    p_data = get_panchang_data(target_dt, not date_str)
    return render(request, 'panchang.html', {'p_data': p_data})

def contact(request):
    msg_sent = False
    if request.method == 'POST':
        n = request.POST.get('name')
        e = request.POST.get('email')
        m = request.POST.get('mobile')
        b = request.POST.get('message')
        
        # 1. JSON में सेव करने वाला आपका पुराना लॉजिक (बैकअप के लिए)
        save_message({
            "name": n,
            "email": e,
            "mobile": m,
            "body": b,
            "time": datetime.now().strftime("%d-%m-%Y %H:%M")
        })
        
        # 🌟 2. नया लॉजिक: इसे सीधा एडमिन के Lead डेटाबेस में सेव करें! 🌟
        Lead.objects.create(
            name=n,
            email=e,
            mobile=m,
            message=b,
            city="संपर्क पेज" # हमें पता रहेगा कि यह लीड कहाँ से आई है
        )
        
        msg_sent = True
    return render(request, 'contact.html', {'msg_sent': msg_sent})

def register_view(request):
    if request.method == 'POST':
        u, p, e = request.POST.get('username'), request.POST.get('password'), request.POST.get('email')
        if not User.objects.filter(username=u).exists():
            user = User.objects.create_user(username=u, email=e, password=p)
            UserProfile.objects.create(user=user)
            return redirect('login')
    return render(request, 'register.html')

def login_view(request):
    if request.method == 'POST':
        u, p = request.POST.get('username'), request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user:
            login(request, user)
            return redirect('home')
    return render(request, 'login.html')

def user_logout(request):
    logout(request)
    return redirect('home')

# --- Admin Dashboard Views ---
def admin_view(request):
    # स्टेट्स कार्ड्स के लिए डेटा
    total_kundalis = SavedKundali.objects.count()
    
    # आज की लीड्स
    today = timezone.now().date()
    today_leads = Lead.objects.filter(created_at__date=today).count()
    
    # रीसेंट एक्टिविटी (आखरी 5 कुंडली)
    recent_activities = SavedKundali.objects.order_by('-created_at')[:5]
    
    context = {
        'total_kundalis': total_kundalis,
        'today_leads': today_leads,
        'recent_activities': recent_activities,
    }
    return render(request, 'admin/dashboard.html', context)

def admin_leads(request):
    if not request.session.get('logged_in'):
        return JsonResponse({"error": "Unauthorized"}, status=401)
    
    stats = {"total": 0, "kundali_total": 0, "panchang_total": 0}
    if os.path.exists(ANALYTICS_FILE):
        with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f:
            stats = json.load(f)
            
    data = {
        "stats": stats,
        "leads": [
            {"Type": "Kundali", "Name": "Sample User", "DOB": "27-04-1995", "City": "Rajkot", "Date": "27-04-2026"}
        ]
    }
    return JsonResponse(data)
def logout_view(request):
    if 'logged_in' in request.session:
        del request.session['logged_in']
    return redirect('admin_view')
