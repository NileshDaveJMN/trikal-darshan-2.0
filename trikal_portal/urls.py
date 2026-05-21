from core.views.kundali_views import home, download_kundali_pdf, api_get_ai_analysis, user_profile_view
from django.contrib import admin
from core.views import milan_views  # 🌟 मिलान व्यूज का बिल्कुल सटीक और सिंगल इम्पोर्ट
from core.views.milan_views import milan_view, calculate_milan_api, save_milan_api
from core.views.panchang_views import panchang
from core.views.auth_views import login_view, register_view, user_logout, submit_payment
from core.views.admin_views import admin_view, admin_leads, contact, logout_view
from django.urls import path, include
from core.views import master_views, auth_views, kundali_views 

urlpatterns = [
    # जांगो का अपना डिफ़ॉल्ट एडमिन पैनल
    path('django-admin/', admin.site.urls), 
    
    # यूजर लॉगिन और रजिस्टर के राउट्स
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', user_logout, name='logout'),
    path('profile/', user_profile_view, name='user_profile'),
    
    # आपके पोर्टल के मेन राउट्स
    path('', home, name='home'),
    path('api/get_ai_analysis/', api_get_ai_analysis, name='api_get_ai_analysis'),
    path('panchang/', panchang, name='panchang'),
    path('contact/', contact, name='contact'),
    path('download-pdf/', download_kundali_pdf, name='download_kundali_pdf'), 
    path('kundali/<int:k_id>/', home, name='view_specific_kundali'),
    path('calc/', kundali_views.kundali_calculation, name='calc_kundali'),
    
    # --- Kundali Milan Routes ---
    path('milan/', milan_view, name='milan'),
    path('api/calculate_milan/', calculate_milan_api, name='api_calculate_milan'),
    path('api/save_milan/', save_milan_api, name='api_save_milan'),
    
    # 📥 प्रीमियम 36 गुण मिलान PDF डाउनलोड करने का अचूक रास्ता
    path('download-milan-pdf/', milan_views.download_milan_pdf, name='download_milan_pdf'),
    
    # आपका कस्टम एडमिन और ट्रैकिंग
    path('admin/', admin_view, name='admin_view'),
    path('admin/leads', admin_leads, name='admin_leads'),
    path('admin-panel/', admin_view, name='admin_view'),
    path('admin-panel/leads', admin_leads, name='admin_leads'),
    
    # पेमेंट राउट 
    path('submit-payment/', submit_payment, name='submit_payment'),
]
