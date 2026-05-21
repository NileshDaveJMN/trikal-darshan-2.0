from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from core.forms import KundaliForm, MilanForm  # Forms upload hone baaki hain
from core.models import UserProfile, SavedKundali

def master_portal_view(request):
    """Trikal Darshan Main Application View (Dynamic Tabs)"""
    context = {}
    
    # 1. Kundali Tab Data (Forms)
    context['k_form'] = KundaliForm()
    
    # 2. Milan Tab Data (Forms)
    context['m_form'] = MilanForm()
    
    # 3. User Tab Data (If Logged In)
    if request.user.is_authenticated:
        try:
            context['user_profile'] = request.user.userprofile
            context['saved_kundalis'] = SavedKundali.objects.filter(user=request.user)
        except UserProfile.DoesNotExist:
            context['user_profile'] = None
    else:
        context['user_profile'] = None
        context['saved_kundalis'] = []
        
    # 4. Panchang Tab Data (Pydroid limit par dummy load karte hain)
    context['panchang_dummy'] = "लोकल मोबाइल सर्वर पर लाइव पंचांग उपलब्ध नहीं है।"

    # Hume forms upload karne honge
    return render(request, 'master_dashboard.html', context)
