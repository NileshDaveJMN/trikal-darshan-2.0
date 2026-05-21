# views/milan_views.py
from django.template.loader import render_to_string
import requests
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required

from core.models import TabSettings, KundaliMilanHistory
from engines.milan_engine import calculate_milan

MONTHS = [
    "जनवरी", "फरवरी", "मार्च", "अप्रैल",
    "मई", "जून", "जुलाई", "अगस्त",
    "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"
]

# =========================================================
# MAIN MILAN PAGE
# =========================================================

def milan_view(request):
    tab_settings = TabSettings.objects.first() or TabSettings.objects.create()

    month_choices = [
        {'val': i + 1, 'name': month}
        for i, month in enumerate(MONTHS)
    ]

    context = {
        'tabs': tab_settings,
        'days': range(1, 32),
        'month_choices': month_choices,
        'years': range(1940, 2027),
        'has_paid': True,   # हमेशा True
    }

    return render(request, 'milan.html', context)


# =========================================================
# CALCULATE MILAN API (WITH CREDIT LOGIC)
# =========================================================
def calculate_milan_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'मिलान देखने के लिए कृपया लॉगिन करें।'})

    if request.method == 'POST':
        # 🌟 नया फिक्स: चेक करें कि क्या यूज़र सेव की हुई हिस्ट्री देख रहा है
        history_id = request.POST.get('history_id')
        if history_id:
            history = KundaliMilanHistory.objects.filter(id=history_id, user=request.user).first()
            if history:
                # सेव की गई इनपुट्स से दोबारा पूरा इंजन रन करें (0 क्रेडिट पर भी चलेगा, कोई कटौती नहीं होगी)
                b_name = history.boy_name
                b_naks = history.boy_nakshatra
                b_rashi = history.boy_rashi
                b_manglik = "yes" in str(history.manglik_status).lower() or "पूर्ण" in str(history.manglik_status)

                g_name = history.girl_name
                g_naks = history.girl_nakshatra
                g_rashi = history.girl_rashi
                g_manglik = "yes" in str(history.manglik_status).lower() or "पूर्ण" in str(history.manglik_status)
                
                milan_result = calculate_milan(b_naks, b_rashi, b_manglik, g_naks, g_rashi, g_manglik)
                
                if "error" in milan_result:
                    return JsonResponse({'status': 'error', 'message': milan_result["error"]})

                return JsonResponse({
                    'status': 'success',
                    'data': milan_result,
                    'names': {'boy': b_name, 'girl': g_name}
                })

        # --- नए मिलान का स्टैंडर्ड फ्लो (क्रेडिट्स चेक और कटौती होगी) ---
        user_profile = request.user.userprofile
        if user_profile.milan_credits <= 0:
            return JsonResponse({
                'status': 'error', 
                'message': '⚠️ आपके मिलान क्रेडिट्स खत्म हो गए हैं! कृपया रिचार्ज करें।'
            })

        b_name = request.POST.get('boy_name', 'Boy')
        b_naks = request.POST.get('boy_naks') or request.POST.get('boy_nakshatra')
        b_rashi = request.POST.get('boy_rashi')
        b_manglik = request.POST.get('boy_manglik') == 'yes'

        g_name = request.POST.get('girl_name', 'Girl')
        g_naks = request.POST.get('girl_naks') or request.POST.get('girl_nakshatra')
        g_rashi = request.POST.get('girl_rashi')
        g_manglik = request.POST.get('girl_manglik') == 'yes'
        
        if not b_naks or not g_naks:
            return JsonResponse({'status': 'error', 'message': 'कृपया दोनों का नक्षत्र चुनें।'})

        milan_result = calculate_milan(b_naks, b_rashi, b_manglik, g_naks, g_rashi, g_manglik)

        if "error" in milan_result:
            return JsonResponse({'status': 'error', 'message': milan_result["error"]})

        # नया मिलान होने पर ही क्रेडिट काटें
        user_profile.milan_credits -= 1
        user_profile.save()

        return JsonResponse({
            'status': 'success',
            'data': milan_result,
            'names': {'boy': b_name, 'girl': g_name}
        })

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

# =========================================================
# SAVE MILAN API
# =========================================================

def save_milan_api(request):
    if request.method == "POST":
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'error', 'message': 'लॉगिन आवश्यक है!'})

        try:
            boy_name = request.POST.get('boy_name')
            girl_name = request.POST.get('girl_name')
            total_score = request.POST.get('total_score')
            is_recommended = request.POST.get('is_recommended') == 'true'
            manglik_status = request.POST.get('manglik_status', '')

            KundaliMilanHistory.objects.create(
                user=request.user,
                boy_name=boy_name,
                boy_nakshatra=request.POST.get('boy_nakshatra', ''),
                boy_rashi=request.POST.get('boy_rashi', ''),
                girl_name=girl_name,
                girl_nakshatra=request.POST.get('girl_nakshatra', ''),
                girl_rashi=request.POST.get('girl_rashi', ''),
                total_score=float(total_score),
                is_recommended=is_recommended,
                manglik_status=manglik_status
            )
            return JsonResponse({'status': 'success', 'message': 'मिलान सफलतापूर्वक सेव हो गया!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
            
    return JsonResponse({'status': 'error', 'message': 'Invalid Request'})


# =========================================================
# PDF DOWNLOAD
# =========================================================

def download_milan_pdf(request):
    # 1. URL से डेटा लेना
    context = {
        'b_name': request.GET.get('b_name', 'वर'),
        'g_name': request.GET.get('g_name', 'कन्या'),
        'b_naks': request.GET.get('b_naks', '-'),
        'g_naks': request.GET.get('g_naks', '-'),
        'b_rashi': request.GET.get('b_rashi', '-'),
        'g_rashi': request.GET.get('g_rashi', '-'),
        'b_manglik': 'हाँ' if request.GET.get('b_manglik') == 'yes' else 'नहीं',
        'g_manglik': 'हाँ' if request.GET.get('g_manglik') == 'yes' else 'नहीं',
        'total_score': request.GET.get('score', '0'),
    }
    
    try:
        score = float(context['total_score'])
        context['is_recommended'] = score >= 18
    except:
        context['is_recommended'] = False

    # 2. HTML डिज़ाइन को तैयार करना
    html_string = render_to_string('milan_pdf.html', context)

    # 3. PDF बनाना (या मोबाइल पर एरर मैसेज दिखाना)
    try:
        from weasyprint import HTML
        pdf_file = HTML(string=html_string).write_pdf()
        
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="milan_report.pdf"'
        return response
    except Exception as e:
        # अगर Pydroid (मोबाइल) पर हैं, तो ऐप क्रैश होने से बचाना
        return HttpResponse("<h3 style='text-align:center; margin-top:50px; color:#e74c3c;'>लोकल मोबाइल सर्वर (Pydroid) पर PDF डाउनलोड सपोर्ट नहीं करता।<br><br>कृपया इसे लाइव सर्वर (PythonAnywhere) पर टेस्ट करें।</h3>")