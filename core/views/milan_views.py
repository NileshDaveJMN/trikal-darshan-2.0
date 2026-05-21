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

# =========================================================
# CALCULATE MILAN API (WITH CREDIT LOGIC)
# =========================================================
def calculate_milan_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'मिलान देखने के लिए कृपया लॉगिन करें।'})

    if request.method == 'POST':
        history_id = request.POST.get('history_id')
        if history_id:
            history = KundaliMilanHistory.objects.filter(id=history_id, user=request.user).first()
            if history:
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

                # 🌟 फिक्स: PDF के लिए डेटा सेशन (मेमोरी) में सेव करें
                request.session['last_milan_result'] = milan_result
                request.session.modified = True

                return JsonResponse({
                    'status': 'success',
                    'data': milan_result,
                    'names': {'boy': b_name, 'girl': g_name}
                })

        # --- नए मिलान का फ्लो ---
        user_profile = request.user.userprofile
        if user_profile.milan_credits <= 0:
            return JsonResponse({'status': 'error', 'message': '⚠️ आपके मिलान क्रेडिट्स खत्म हो गए हैं! कृपया रिचार्ज करें।'})

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

        user_profile.milan_credits -= 1
        user_profile.save()

        # 🌟 फिक्स: PDF के लिए डेटा सेशन (मेमोरी) में सेव करें
        request.session['last_milan_result'] = milan_result
        request.session.modified = True

        return JsonResponse({
            'status': 'success',
            'data': milan_result,
            'names': {'boy': b_name, 'girl': g_name}
        })

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


# =========================================================
# PDF DOWNLOAD
# =========================================================
def download_milan_pdf(request):
    # 1. URL से डेटा निकालना (चाहे किसी भी नाम से आया हो)
    b_name = request.GET.get('b_name', 'वर')
    g_name = request.GET.get('g_name', 'कन्या')
    b_naks = request.GET.get('b_naks') or request.GET.get('boy_nakshatra') or '-'
    g_naks = request.GET.get('g_naks') or request.GET.get('girl_nakshatra') or '-'
    b_rashi = request.GET.get('b_rashi', '-')
    g_rashi = request.GET.get('g_rashi', '-')
    b_manglik = request.GET.get('b_manglik') == 'yes'
    g_manglik = request.GET.get('g_manglik') == 'yes'

    # 2. ब्रह्मास्त्र: इंजन से सीधा दोबारा कैलकुलेट करना (ताकि डेटा कभी मिस न हो)
    from engines.milan_engine import calculate_milan
    milan_result = calculate_milan(b_naks, b_rashi, b_manglik, g_naks, g_rashi, g_manglik)
    
    # 3. बैकअप: अगर URL में नाम नहीं आया, तो Session (Memory) से उठाना
    if not milan_result or "error" in milan_result or not milan_result.get("breakdown"):
        milan_result = request.session.get('last_milan_result', {})

    breakdown = milan_result.get("breakdown", {})
    remedies = milan_result.get("remedies", [])

    context = {
        'b_name': b_name, 'g_name': g_name,
        'b_naks': b_naks, 'g_naks': g_naks,
        'b_rashi': b_rashi, 'g_rashi': g_rashi,
        'b_manglik': 'हाँ' if b_manglik else 'नहीं',
        'g_manglik': 'हाँ' if g_manglik else 'नहीं',
        'total_score': request.GET.get('score', milan_result.get('total_score', '0')),
        'breakdown': breakdown,
        'remedies': remedies,
    }
    
    try:
        score = float(context['total_score'])
        context['is_recommended'] = score >= 18
    except:
        context['is_recommended'] = False

    from django.template.loader import render_to_string
    html_string = render_to_string('milan_pdf.html', context)

    try:
        from weasyprint import HTML
        from django.http import HttpResponse
        pdf_file = HTML(string=html_string).write_pdf()
        
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="milan_report.pdf"'
        return response
    except Exception as e:
        from django.http import HttpResponse
        return HttpResponse(f"<h3 style='text-align:center; margin-top:50px; color:#e74c3c;'>PDF बनाने में त्रुटि: {str(e)}</h3>")
