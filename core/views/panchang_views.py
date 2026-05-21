# views/panchang_views.py
from django.shortcuts import render
from datetime import datetime
from engines.panchang_engine import get_panchang_data

def panchang(request):
    date_str = request.GET.get('date')
    
    if date_str:
        target_dt = datetime.strptime(date_str, "%Y-%m-%d")
        target_dt = target_dt.replace(hour=12, minute=0, second=0)
    else:
        target_dt = datetime.now()

    p_data = get_panchang_data(target_dt, not date_str)
    current_date_value = target_dt.strftime("%Y-%m-%d")
    return render(request, 'panchang.html', {'p_data': p_data, 'current_date_value': current_date_value})
