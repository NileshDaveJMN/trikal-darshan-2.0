# views/admin_views.py
import os
import json
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings
from core.models import SavedKundali, Lead

BASE_DIR = settings.BASE_DIR
MSG_FILE = os.path.join(BASE_DIR, 'messages.json')
ANALYTICS_FILE = os.path.join(BASE_DIR, 'analytics.json')

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

def contact(request):
    msg_sent = False
    if request.method == 'POST':
        n, e, m, b = request.POST.get('name'), request.POST.get('email'), request.POST.get('mobile'), request.POST.get('message')
        save_message({"name": n, "email": e, "mobile": m, "body": b, "time": datetime.now().strftime("%d-%m-%Y %H:%M")})
        Lead.objects.create(name=n, email=e, mobile=m, message=b, city="संपर्क पेज")
        msg_sent = True
    return render(request, 'contact.html', {'msg_sent': msg_sent})

def admin_view(request):
    total_kundalis = SavedKundali.objects.count()
    today = timezone.now().date()
    today_leads = Lead.objects.filter(created_at__date=today).count()
    recent_activities = SavedKundali.objects.order_by('-created_at')[:5]
    
    context = {'total_kundalis': total_kundalis, 'today_leads': today_leads, 'recent_activities': recent_activities}
    return render(request, 'admin/dashboard.html', context)

def admin_leads(request):
    if not request.session.get('logged_in'): return JsonResponse({"error": "Unauthorized"}, status=401)
    stats = {"total": 0, "kundali_total": 0, "panchang_total": 0}
    if os.path.exists(ANALYTICS_FILE):
        with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f: stats = json.load(f)
    return JsonResponse({"stats": stats, "leads": [{"Type": "Kundali", "Name": "Sample User", "DOB": "27-04-1995", "City": "Rajkot", "Date": "27-04-2026"}]})

def logout_view(request):
    if 'logged_in' in request.session: del request.session['logged_in']
    return redirect('admin_view')
from django.http import JsonResponse
from core.models import KundaliMilanHistory  # Aapka purana model

def save_milan_api(request):
    if request.method == "POST":
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'error', 'message': 'लॉगिन आवश्यक है!'})

        try:
            # Form aur AJAX se data nikalna
            boy_name = request.POST.get('boy_name')
            girl_name = request.POST.get('girl_name')
            total_score = request.POST.get('total_score')
            is_recommended = request.POST.get('is_recommended') == 'true'
            manglik_status = request.POST.get('manglik_status', '')

            # Aapke purane model mein data save karna
            KundaliMilanHistory.objects.create(
                user=request.user,
                boy_name=boy_name,
                girl_name=girl_name,
                total_score=float(total_score),
                is_recommended=is_recommended,
                manglik_status=manglik_status
            )
            return JsonResponse({'status': 'success', 'message': 'मिलान सफलतापूर्वक सेव हो गया!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
            
    return JsonResponse({'status': 'error', 'message': 'Invalid Request'})
