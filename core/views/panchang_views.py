# views/panchang_views.py
from django.shortcuts import render
from datetime import datetime
from engines.panchang_engine import get_panchang_data

def panchang(request):
    date_str = request.GET.get('date')
    
    # 1. URL से यूज़र द्वारा चुना गया lat, lon और city निकालें
    user_lat = request.GET.get('lat', '28.5839')   # डिफ़ॉल्ट Lat (नई दिल्ली)
    user_lon = request.GET.get('lon', '77.2090')   # डिफ़ॉल्ट Lon (नई दिल्ली)
    current_city = request.GET.get('city', 'नई दिल्ली')
    
    if date_str:
        target_dt = datetime.strptime(date_str, "%Y-%m-%d")
        target_dt = target_dt.replace(hour=12, minute=0, second=0)
    else:
        target_dt = datetime.now()

    # 2. आपके p_data वेरिएबल में lat और lon पास करें
    p_data = get_panchang_data(target_dt, not date_str, float(user_lat), float(user_lon))
    
    # 3. शहर का नाम p_data डिक्शनरी में डाल दें ताकि HTML में दिखा सकें
    if p_data:  # चेक कर लें कि डेटा खाली तो नहीं है
        p_data['current_city'] = current_city
        
    current_date_value = target_dt.strftime("%Y-%m-%d")
    
    return render(request, 'panchang.html', {
        'p_data': p_data, 
        'current_date_value': current_date_value
    })
