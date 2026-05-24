from core.views.kundali_views import home, download_kundali_pdf, api_get_ai_analysis, user_profile_view
from django.contrib import admin
from core.views import milan_views
from core.views.milan_views import milan_view, calculate_milan_api, save_milan_api
from core.views.panchang_views import panchang
from core.views.auth_views import login_view, register_view, user_logout, submit_payment
from core.views.admin_views import admin_view, admin_leads, contact, logout_view
from django.urls import path, include
from core.views import master_views, auth_views, kundali_views
from core.views.kundali_views import save_onboarding
from core.views.telegram_webhook_view import telegram_webhook
from core.views.trikal_api_views import api_save_chat_id, api_pending_horoscope, api_save_horoscope

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('login/',    login_view,    name='login'),
    path('api/bot/send-horoscope/', api_send_daily_horoscope, name='api_send_horoscope'),
    path('register/', register_view, name='register'),
    path('logout/',   user_logout,   name='logout'),
    path('profile/',  user_profile_view, name='user_profile'),
    path('',          home,          name='home'),
    path('api/get_ai_analysis/', api_get_ai_analysis, name='api_get_ai_analysis'),
    path('panchang/', panchang,      name='panchang'),
    path('contact/',  contact,       name='contact'),
    path('download-pdf/', download_kundali_pdf, name='download_kundali_pdf'),
    path('kundali/<int:k_id>/', home, name='view_specific_kundali'),
    path('calc/',     kundali_views.kundali_calculation, name='calc_kundali'),
    path('milan/',    milan_view,    name='milan'),
    path('api/calculate_milan/', calculate_milan_api, name='api_calculate_milan'),
    path('api/save_milan/',      save_milan_api,      name='api_save_milan'),
    path('download-milan-pdf/', milan_views.download_milan_pdf, name='download_milan_pdf'),
    path('admin/',          admin_view,   name='admin_view'),
    path('admin/leads',     admin_leads,  name='admin_leads'),
    path('admin-panel/',    admin_view,   name='admin_view'),
    path('admin-panel/leads', admin_leads, name='admin_leads'),
    path('submit-payment/', submit_payment,  name='submit_payment'),
    path('onboarding/',     save_onboarding, name='save_onboarding'),
    path('telegram-webhook/', telegram_webhook, name='telegram_webhook'),
    # 🌟 Render Bot APIs
    path('api/bot/save-chat-id/',      api_save_chat_id,      name='api_save_chat_id'),
    path('api/bot/pending-horoscope/', api_pending_horoscope, name='api_pending_horoscope'),
    path('api/bot/save-horoscope/',    api_save_horoscope,    name='api_save_horoscope'),
]
