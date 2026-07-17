import os
import json
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.contrib import messages
from django.template.loader import get_template
from django.contrib.auth.decorators import login_required
from core.models import SavedKundali, TabSettings, AIQuestionHistory, KundaliMilanHistory, UserProfile, UserNotification, LearnCategory, AIChatSession, AIChatMessage
# WeasyPrint Integration
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    HTML = None
    WEASYPRINT_AVAILABLE = False

from core.views.rashifal_views import RASHI_LIST
from engines.festival_alerts import get_today_festivals
from engines.dosha_analyzer import analyze_doshas, recommend_gemstone
from engines.kundali_engine import get_kundali_data
from engines.panchang_engine import get_panchang_data

MONTHS = ["जनवरी", "फरवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]
ANALYTICS_FILE = os.path.join(settings.BASE_DIR, 'analytics.json')

def update_analytics(page_type):
    stats = {"total": 0, "kundali_total": 0, "panchang_total": 0}
    if os.path.exists(ANALYTICS_FILE):
        with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f:
            try: stats = json.load(f)
            except: pass
    
    stats["total"] += 1
    if page_type == 'kundali': stats["kundali_total"] += 1
    elif page_type == 'panchang': stats["panchang_total"] += 1
        
    with open(ANALYTICS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=4)

def home(request, k_id=None):
    if request.user.is_authenticated:
        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if not user_profile.primary_focus:
            return redirect('save_onboarding')
            
    tab_settings = TabSettings.objects.first() or TabSettings.objects.create()

    if request.method == 'GET':
        try: update_analytics('kundali') 
        except: pass
        
    res = None
    saved_kundalis = []
    saved_milans = []
    user_notifications = [] # 🚀 नया
    unread_notifications_count = 0
    learn_categories = LearnCategory.objects.prefetch_related('items').all() # 🚀 नया
    
    if request.user.is_authenticated:
        saved_kundalis = SavedKundali.objects.filter(user=request.user).order_by('-created_at')
        saved_milans = KundaliMilanHistory.objects.filter(user=request.user).order_by('-created_at')
        user_notifications = UserNotification.objects.filter(user=request.user).order_by('-created_at')[:50] # 🚀 नया
        unread_notifications_count = UserNotification.objects.filter(user=request.user, is_read=False).count()

    if request.method == 'POST':
        def s_int(v): return int(v) if v and str(v).strip() else 0
        def s_float(v): return float(v) if v and str(v).strip() else 0.0

        n = request.POST.get('name')
        g = request.POST.get('gender')
        d, m, y = s_int(request.POST.get('dd')), s_int(request.POST.get('mm')), s_int(request.POST.get('yyyy'))
        h, min_m, s = s_int(request.POST.get('hh')), s_int(request.POST.get('min')), s_int(request.POST.get('sec'))
        c = request.POST.get('city_name')
        lat, lon = s_float(request.POST.get('lat')), s_float(request.POST.get('lon'))

        action = request.POST.get('action')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if is_ajax and action == 'get_ai':
            current_id = request.session.get('current_kundali_id')
            if not current_id:
                return JsonResponse({'status': 'error', 'message': 'कृपया पहले कोई कुंडली चुनें।'})

            kundali = SavedKundali.objects.filter(id=current_id, user=request.user).first()
            if not kundali:
                return JsonResponse({'status': 'error', 'message': 'डेटाबेस में कुंडली नहीं मिली।'})

            topics_raw = request.POST.get('topics', '')
            topics_list = sorted([t.strip() for t in topics_raw.split(',') if t.strip()] if not request.POST.getlist('topics') else request.POST.getlist('topics'))
            custom_q = request.POST.get('custom_question', '').strip()
            
            k_key = f"ai_cache_id_{current_id}"
            ai_cache = request.session.get(k_key, {})
            
            cached_blocks, topics_to_fetch = [], []
            for t in topics_list:
                if t in ai_cache: cached_blocks.append(ai_cache[t])
                else: topics_to_fetch.append(t)
                    
            custom_key = f"CUSTOM_{custom_q}" if custom_q else None
            need_custom_fetch = False
            
            if custom_key:
                if custom_key in ai_cache: cached_blocks.append(ai_cache[custom_key])
                else: need_custom_fetch = True
            
            if not topics_to_fetch and not need_custom_fetch:
                final_sorted = [ai_cache[t] for t in topics_list if t in ai_cache]
                if custom_key and custom_key in ai_cache: final_sorted.append(ai_cache[custom_key])
                return JsonResponse({'status': 'success', 'ai_data': final_sorted, 'source': 'smart_cache'})

            res_ai = get_kundali_data(
                kundali.name, kundali.gender, kundali.day, kundali.month, kundali.year, 
                kundali.hour, kundali.minute, kundali.second, kundali.city, kundali.lat, kundali.lon, 
                need_ai=True, selected_topics=topics_to_fetch, custom_question=custom_q if need_custom_fetch else ""
            )
            
            if res_ai and res_ai.get('predictions'):
                new_ai_blocks = res_ai['predictions']
                if new_ai_blocks and new_ai_blocks[0].get('topic_id') == 'ERROR':
                    return JsonResponse({'status': 'success', 'ai_data': new_ai_blocks})
                
                for item in new_ai_blocks:
                    t_id = item.get('topic_id')
                    if t_id == 'SPECIAL_QUERY' and need_custom_fetch: ai_cache[custom_key] = item
                    elif t_id and t_id != 'SPECIAL_QUERY': ai_cache[t_id] = item
                        
                request.session[k_key] = ai_cache
                request.session.modified = True
                
                final_sorted = [ai_cache[t] for t in topics_list if t in ai_cache]
                if custom_key and custom_key in ai_cache: final_sorted.append(ai_cache[custom_key])
                
                if custom_q and request.user.is_authenticated:
                    colors = ['#e67e22', '#8e44ad', '#27ae60', '#c0392b', '#2980b9']
                    html_to_save = "".join([
                        f"<div style='background: #ffffff; border-left: 6px solid {colors[idx % len(colors)]}; border-radius: 10px; padding: 18px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); margin-bottom:15px;'><h3 style='color: #2c3e50; margin-top: 0; margin-bottom: 10px; font-size: 18px; border-bottom: 1px dashed #bdc3c7; padding-bottom: 8px;'>✨ {pred.get('planet_name', '')}</h3><div style='color: #34495e; font-size: 15px; line-height: 1.6;'>{pred.get('text', '')}</div></div>"
                        for idx, pred in enumerate(new_ai_blocks) if pred.get('topic_id') != 'DEBUG'
                    ])
                    if html_to_save:
                        AIQuestionHistory.objects.create(kundali=kundali, question=custom_q, answer=html_to_save)

                return JsonResponse({'status': 'success', 'ai_data': final_sorted})
            return JsonResponse({'status': 'error', 'message': 'AI इंजन ने डेटा जनरेट नहीं किया।'})


        elif is_ajax and action == 'ai_chat':
            import requests as req
            import random

            current_id = request.session.get('current_kundali_id')
            if not current_id:
                return JsonResponse({'status': 'error', 'message': 'कृपया पहले कोई कुंडली चुनें।'})

            kundali = SavedKundali.objects.filter(id=current_id, user=request.user).first()
            if not kundali:
                return JsonResponse({'status': 'error', 'message': 'कुंडली नहीं मिली।'})

            user_message = request.POST.get('message', '').strip()
            session_id   = request.POST.get('session_id', '').strip()

            if not user_message:
                return JsonResponse({'status': 'error', 'message': 'Message empty'})

            # Session: naya ya existing
            if session_id:
                try:
                    chat_session = AIChatSession.objects.get(id=session_id, kundali=kundali)
                except AIChatSession.DoesNotExist:
                    chat_session = AIChatSession.objects.create(
                        kundali=kundali, title=user_message[:50]
                    )
            else:
                chat_session = AIChatSession.objects.create(
                    kundali=kundali, title=user_message[:50]
                )

            # User message DB mein save
            AIChatMessage.objects.create(session=chat_session, role='user', content=user_message)

            # Last 10 messages → conversation history
            recent_msgs = list(chat_session.messages.order_by('created_at'))
            history_text = "\n".join([
                f"{'User' if m.role == 'user' else 'AI'}: {m.content}"
                for m in recent_msgs
            ])

            # Gemini prompt — full kundali data session se nikalo
            import datetime as _dt
            current_date_str = _dt.datetime.now().strftime("%d %B, %Y")

            kd = request.session.get('kundali_data') or {}

            # 🚀 FIX: planet_details - Case Insensitive Mapping Fix
            planet_lines = ""
            try:
                planet_raw = kd.get('planet_details', {})
                if isinstance(planet_raw, list):
                    planet_raw = {str(p.get('name', p.get('planet', ''))).strip().capitalize(): p for p in planet_raw if isinstance(p, dict)}
                elif isinstance(planet_raw, dict):
                    planet_raw = {str(k).strip().capitalize(): v for k, v in planet_raw.items()}

                planet_map = {
                    'Sun': 'सूर्य', 'Moon': 'चंद्र', 'Mars': 'मंगल',
                    'Mercury': 'बुध', 'Jupiter': 'गुरु', 'Venus': 'शुक्र',
                    'Saturn': 'शनि', 'Rahu': 'राहु', 'Ketu': 'केतु'
                }
                for eng, hin in planet_map.items():
                    p = planet_raw.get(eng, {})
                    if p:
                        house = p.get('house', p.get('house_num', ''))
                        rashi = p.get('rashi', p.get('sign', p.get('rashi_name', '')))
                        retro = ' (वक्री)' if p.get('is_retro') or p.get('retro') else ''
                        planet_lines += f"  - {hin}: {rashi}, {house}वाँ भाव{retro}\n"
            except Exception:
                planet_lines = "  - Data available nahi\n"

            # Dasha info
            dasha_info = "  - Data available nahi"
            try:
                current_dasha = kd.get('current_dasha', '')
                current_antardasha = kd.get('current_antardasha', '')
                if current_dasha:
                    dasha_info = f"  - महादशा: {current_dasha}"
                    if current_antardasha:
                        dasha_info += f", अंतर्दशा: {current_antardasha}"
            except Exception:
                pass

            # Dosha info
            dosha_info = "Data available nahi"
            try:
                doshas = kd.get('detected_doshas', {})
                if isinstance(doshas, dict) and doshas:
                    dosha_list = [name for name, val in doshas.items() if val]
                    dosha_info = ", ".join(dosha_list) if dosha_list else "कोई मुख्य दोष नहीं"
            except Exception:
                pass

            # Yoga info
            yoga_info = "Data available nahi"
            try:
                yogas = kd.get('yogas', [])
                if yogas:
                    yoga_names = [y.get('name', '') for y in yogas if isinstance(y, dict) and y.get('name')]
                    yoga_info = ", ".join(yoga_names[:5]) if yoga_names else "Data available nahi"
            except Exception:
                pass

            prompt = (
                f"Aaj ki tarikh: {current_date_str}\n\n"
                "Tu Trikal Darshan ka AI Jyotish assistant hai — naam \"Trikal AI\".\n"
                "Tu sirf Vedic jyotish, kundali, graha, rashi, dasha, yoga aur spiritual topics par jawab deta hai.\n"
                "Agar koi aur topic ho toh politely bol de.\n\n"
                "=== User ki Sampurn Kundali ===\n\n"
                "Janm Vivaran:\n"
                f"  - Naam: {kundali.name}\n"
                f"  - Ling: {kundali.gender}\n"
                f"  - Janm Tithi: {kundali.day}/{kundali.month}/{kundali.year}\n"
                f"  - Janm Samay: {kundali.hour:02d}:{kundali.minute:02d}:{kundali.second:02d}\n"
                f"  - Janm Sthan: {kundali.city}\n\n"
                "Lagna aur Rashi:\n"
                f"  - Lagna: {kd.get('lagna', kd.get('ascendant', 'N/A'))}\n"
                f"  - Chandra Rashi: {kd.get('chandra_rashi', kd.get('moon_sign', 'N/A'))}\n"
                f"  - Surya Rashi: {kd.get('surya_rashi', kd.get('sun_sign', 'N/A'))}\n"
                f"  - Nakshatra: {kd.get('nakshatra', 'N/A')}\n\n"
                "Graha Sthiti:\n"
                f"{planet_lines}"
                "Vimshottari Dasha:\n"
                f"{dasha_info}\n\n"
                "Dosha:\n"
                f"  - {dosha_info}\n\n"
                "Pramukh Yoga:\n"
                f"  - {yoga_info}\n\n"
                "=== Pichli Baatcheet ===\n"
                f"{history_text}\n\n"
                "=== Niyam ===\n"
                "1. Upar diye SAMPURN kundali data ka upyog karke jawab de — lagna, graha, dasha sab yaad rakho\n"
                "2. Jawab Hindi mein de — simple, warm aur friendly tone\n"
                "3. 3-4 paragraph se zyada nahi\n"
                "4. Koi Markdown (**, ##) mat use karo\n"
                "5. Har jawab mein kundali ke specific details mention karo\n"
                "6. Practical aur positive guidance de"
            )

            # Gemini API call (same pattern as prediction_engine.py)
            from engines.prediction_engine import GEMINI_API_KEYS
            keys = GEMINI_API_KEYS.copy()
            random.shuffle(keys)

            ai_reply = "माफ करें, AI सर्वर अभी व्यस्त है। कृपया कुछ देर बाद पुनः प्रयास करें।"

            for api_key in keys:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={api_key}"
                try:
                    import urllib3
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    resp = req.post(
                        url,
                        json={"contents": [{"parts": [{"text": prompt}]}]},
                        timeout=30,
                        verify=False
                    )
                    if resp.status_code == 200:
                        res_json = resp.json()
                        candidates = res_json.get('candidates', [])
                        if candidates and candidates[0].get('finishReason') != 'SAFETY':
                            parts = candidates[0].get('content', {}).get('parts', [])
                            if parts:
                                ai_reply = parts[0]['text'].replace("**", "").replace("##", "").strip()
                                break
                except Exception:
                    continue

            # Assistant reply save
            AIChatMessage.objects.create(session=chat_session, role='assistant', content=ai_reply)
            chat_session.save()

            return JsonResponse({
                'status':        'success',
                'reply':         ai_reply,
                'session_id':    chat_session.id,
                'session_title': chat_session.title,
            })

        elif is_ajax and action == 'get_chat_history':
            session_id = request.POST.get('session_id', '').strip()
            try:
                chat_session = AIChatSession.objects.get(id=session_id, kundali__user=request.user)
                return JsonResponse({
                    'status': 'success',
                    'messages': [
                        {
                            'role':    msg.role,
                            'content': msg.content,
                            'time':    msg.created_at.strftime('%I:%M %p'),
                        }
                        for msg in chat_session.messages.all()
                    ]
                })
            except AIChatSession.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Session not found'})

        elif action == 'delete_kundali':
            k_id_to_del = request.POST.get('kundali_id')
            if request.user.is_authenticated and k_id_to_del:
                SavedKundali.objects.filter(id=k_id_to_del, user=request.user).delete()
                if request.session.get('current_kundali_id') == int(k_id_to_del):
                    del request.session['current_kundali_id']
                messages.success(request, "कुंडली हटा दी गई।")
            return redirect('home')
            
        elif action == 'delete_all_kundali':
            if request.user.is_authenticated:
                SavedKundali.objects.filter(user=request.user).delete()
                if 'current_kundali_id' in request.session: del request.session['current_kundali_id']
                for key in list(request.session.keys()):
                    if key.startswith('ai_cache_'): del request.session[key]
                messages.success(request, "सभी कुंडलियां डिलीट कर दी गई हैं।")
            return redirect('home')
            
        elif action == "delete_milan":
            milan_id = request.POST.get('milan_id')
            if milan_id and request.user.is_authenticated:
                KundaliMilanHistory.objects.filter(id=milan_id, user=request.user).delete()
                messages.success(request, "मिलान हिस्ट्री से हटा दिया गया है।")
            return redirect('/?tab=view-milan')
            
        elif not action or action == 'calc':
            if request.user.is_authenticated:
                user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
                if user_profile.kundali_credits > 0:
                    new_k = SavedKundali.objects.create(user=request.user, name=n, gender=g, day=d, month=m, year=y, hour=h, minute=min_m, second=s, city=c, lat=lat, lon=lon)
                    user_profile.kundali_credits -= 1
                    user_profile.save()
                    messages.success(request, f"✅ {n} की कुंडली सफलतापूर्वक बन गई है! (बाकी क्रेडिट: {user_profile.kundali_credits})")
                    return redirect('view_specific_kundali', k_id=new_k.id)
                else:
                    messages.error(request, "⚠️ आपके कुंडली क्रेडिट्स खत्म हो गए हैं! नई कुंडली बनाने के लिए कृपया रिचार्ज करें।")
                    return redirect('/?tab=view-user')
            else:
                res = get_kundali_data(n, g, d, m, y, h, min_m, s, c, lat, lon, need_ai=False)

    ai_history = []
    if k_id and request.user.is_authenticated:
        kundali = SavedKundali.objects.filter(id=k_id, user=request.user).first()
        if kundali:
            res = get_kundali_data(
                kundali.name, kundali.gender, kundali.day, kundali.month, kundali.year,
                kundali.hour, kundali.minute, kundali.second, kundali.city, kundali.lat, kundali.lon
            )
            request.session['current_kundali_id'] = k_id
            request.session['kundali_data'] = res
            
            for record in AIQuestionHistory.objects.filter(kundali=kundali).order_by('-created_at'):
                ai_history.append({'question': record.question, 'answer': record.answer})
        else:
            return redirect('home')

    if res and 'houses' in res and 'planet_details' in res:
        res['detected_doshas'] = analyze_doshas({str(h["num"]): h for h in res["houses"]}, res['planet_details'])
        if 'lagna' in res:
            res['gemstone'] = recommend_gemstone(res['lagna'])
            
        # 🚀 FIX: Update session state for 'detected_doshas' and 'gemstone' so AI chat can access them
        if k_id and request.user.is_authenticated:
            request.session['kundali_data'] = res
            request.session.modified = True
            
        # 🚀 FIX: p_extra (sunrise-based panchang) hataya gaya — chart_tab.html ab
        # kundali_engine ke apne birth-exact-moment fields (res.tithi, res.nakshatra,
        # res.chandra_rashi, res.paksha, res.hindu_month, res.vara, res.yoga, res.karana)
        # directly use karta hai, jo zyada accurate hain (sunrise ke bajaye exact birth time par).

    target_dt = datetime.now()
    user_lat, user_lon, current_city = 28.5839, 77.2090, 'नई दिल्ली'

    if request.user.is_authenticated:
        try:
            prof = request.user.userprofile
            if prof.default_lat and prof.default_lon:
                user_lat, user_lon, current_city = prof.default_lat, prof.default_lon, prof.default_city or 'नई दिल्ली'
        except Exception: pass

    # Panchang Data & Festival Logic
    p_data = get_panchang_data(target_dt, True, float(user_lat), float(user_lon))
    today_festivals = []
    
    if p_data:
        p_data['current_city'] = current_city
        today_festivals = get_today_festivals(p_data)

    # 🚀 Context में कॉमा (,) की गलती सुधार ली गई है
    context = {
        'tabs': tab_settings,  
        'res': res, 
        'current_k_id': k_id,
        'days': range(1, 32), 
        'month_choices': [{'val': i+1, 'name': month} for i, month in enumerate(MONTHS)],
        'years': range(1940, 2027), 
        'hours': range(0, 24),
        'minutes': range(0, 60), 
        'seconds': range(0, 60),
        'saved_kundalis': saved_kundalis, 
        'kundali_data': request.session.get('kundali_data'),
        'ai_history': ai_history,
        'saved_milans': saved_milans,
        'p_data': p_data,
        'today_festivals': today_festivals,
        'current_date_value': target_dt.strftime("%Y-%m-%d"),
        'rashis': RASHI_LIST,
        'user_notifications': user_notifications,
        'unread_notifications_count': unread_notifications_count,
        'learn_categories': learn_categories,
        'chat_sessions': list(
            AIChatSession.objects.filter(
                kundali__user=request.user,
                kundali_id=k_id
            ).order_by('-updated_at').values('id', 'title', 'created_at')[:20]
        ) if (request.user.is_authenticated and k_id) else [],
    }
            
    return render(request, 'home.html', context)

def download_kundali_pdf(request):
    if not WEASYPRINT_AVAILABLE:
        return HttpResponse("लोकल मोबाइल सर्वर पर PDF डाउनलोड सपोर्ट नहीं करता। कृपया इसे लाइव सर्वर पर टेस्ट करें।", status=501)
        
    data = request.session.get('kundali_data')
    if not data: 
        return HttpResponse("डेटा नहीं मिला।")
        
    # 🚀 FIX: पहले यहाँ sunrise-based panchang (p_extra) tithi/paksha/samvat ko
    # overwrite kar deta था — ab kundali_engine ke apne birth-exact-moment
    # values (data['tithi'], data['paksha'], data['samvat'], data['hindu_month'])
    # hi PDF me use honge, jo already sahi hain.
    data['hindu_maas'] = data.get('hindu_month', '')
        
    ai_data_list = []
    if request.POST.get('include_ai') == 'yes':
        current_k_id = request.session.get('current_kundali_id')
        ai_cache = request.session.get(f"ai_cache_id_{current_k_id}", {})
        
        combined_html = "".join([
            f"<div style='margin-bottom:15px;'><h4 style='color:#2980b9; margin:5px 0;'>{block.get('planet_name', '')}</h4>{block.get('text', '')}</div>"
            for t_id, block in ai_cache.items() if not t_id.startswith('CUSTOM_')
        ])
        if combined_html:
            ai_data_list.append({'question': 'विभिन्न विषयों पर AI फलित', 'answer': combined_html})
        
        if request.user.is_authenticated and current_k_id:
            kundali = SavedKundali.objects.filter(id=current_k_id, user=request.user).first()
            if kundali:
                for h in AIQuestionHistory.objects.filter(kundali=kundali).order_by('-created_at'):
                    ai_data_list.append({'question': h.question, 'answer': h.answer})

    data.update({
        'include_charts': request.POST.get('include_charts') == 'yes',
        'include_planets': request.POST.get('include_planets') == 'yes',
        'include_ai': request.POST.get('include_ai') == 'yes',
        'include_dosha': request.POST.get('include_dosha') == 'yes',
        'chart_image': request.POST.get('chart_image_data'),
        'ai_history': ai_data_list
    })

    pdf_file = HTML(string=get_template('kundali_pdf.html').render(data), base_url=request.build_absolute_uri()).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Trikal_Darshan_Report.pdf"'
    return response

def api_get_ai_analysis(request):
    if request.method == 'POST':
        try:
            current_id = request.session.get('current_kundali_id')
            if not current_id: return JsonResponse({"status": "error", "message": "कुंडली सिलेक्टेड नहीं है।"})
            
            kundali = SavedKundali.objects.filter(id=current_id, user=request.user).first()
            if not kundali: return JsonResponse({"status": "error", "message": "रिकॉर्ड नहीं मिला।"})

            topics_raw = request.POST.getlist('topics') or request.POST.get('topics', '').split(',')
            selected_topics = sorted([t.strip() for t in topics_raw if t.strip()])
            custom_question = request.POST.get('custom_question', '').strip()
            
            query_text = custom_question if custom_question else "विषय: " + ", ".join(selected_topics)
            if query_text == request.session.get('ai_last_query', '') and request.session.get('ai_last_response'):
                return JsonResponse({"status": "success", "predictions": request.session['ai_last_response']})

            res = get_kundali_data(
                kundali.name, kundali.gender, kundali.day, kundali.month, kundali.year,
                kundali.hour, kundali.minute, kundali.second, kundali.city, kundali.lat, kundali.lon,
                need_ai=True, selected_topics=selected_topics, custom_question=custom_question
            )
            
            if res and res.get('predictions'):
                request.session['ai_last_query'] = query_text
                request.session['ai_last_response'] = res['predictions']
                request.session.modified = True
                
                if custom_question:
                    AIQuestionHistory.objects.create(kundali=kundali, question=custom_question, answer=json.dumps(res['predictions'], ensure_ascii=False))
                        
                return JsonResponse({"status": "success", "predictions": res['predictions']})
            return JsonResponse({"status": "error", "message": "AI सर्वर व्यस्त है।"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid request"})

@login_required(login_url='/login/')
def user_profile_view(request):
    return render(request, 'user_profile.html')

def kundali_calculation(request):
    return HttpResponse("कैलकुलेशन इंजन अभी जोड़ा नहीं गया है। हम अभी सिर्फ डिज़ाइन टेस्ट कर रहे हैं।")

@login_required(login_url='/login/')
def save_onboarding(request):
    if request.method == 'POST':
        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        user_profile.primary_focus = ", ".join(request.POST.getlist('primary_focus'))
        user_profile.current_challenge = ", ".join(request.POST.getlist('current_challenge'))
        user_profile.profession = ", ".join(request.POST.getlist('profession'))
        user_profile.travel_habit = ", ".join(request.POST.getlist('travel_habit'))
        user_profile.relationship_status = request.POST.get('relationship_status', '')
        user_profile.save()
        return redirect('home') 
        
    return render(request, 'onboarding.html')

def ping(request):
    return HttpResponse("ok", content_type="text/plain")

def mark_notifications_read(request):
    if request.user.is_authenticated and request.method == "POST":
        UserNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({"status": "ok"})
    return JsonResponse({"status": "error"})