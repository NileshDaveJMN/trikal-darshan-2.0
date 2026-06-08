from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from core.views.hast_rekha_view import hast_rekha_view, api_analyze_hast_rekha, api_delete_hast_reading

# Views Imports
from core.views.kundali_views import home, download_kundali_pdf, api_get_ai_analysis, user_profile_view, save_onboarding, ping, kundali_calculation, mark_notifications_read
from core.views.milan_views import milan_view, calculate_milan_api, save_milan_api, download_milan_pdf
from core.views.panchang_views import panchang, save_default_location, clear_default_location
from core.views.auth_views import login_view, register_view, user_logout, submit_payment
from core.views.admin_views import admin_view, admin_leads, contact
from core.views.rashifal_views import rashifal_home, rashifal_detail, api_rashifal
from core.views.seo_views import sitemap_xml
from core.views.push_views import get_vapid_public_key, save_push_subscription, delete_push_subscription, admin_send_notification
from core.views.trikal_api_views import api_send_daily_horoscope

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('ping/', ping, name='ping'),

    # Auth
    path('login/',    login_view,    name='login'),
    path('register/', register_view, name='register'),
    path('logout/',   user_logout,   name='logout'),
    path('profile/',  user_profile_view, name='user_profile'),
    path('sitemap.xml', sitemap_xml, name='sitemap'),

    # Main
    path('',          home,          name='home'),
    path('api/get_ai_analysis/', api_get_ai_analysis, name='api_get_ai_analysis'),
    path('panchang/', panchang,      name='panchang'),
    path('contact/',  contact,       name='contact'),
    path('download-pdf/', download_kundali_pdf, name='download_kundali_pdf'),
    path('kundali/<int:k_id>/', home, name='view_specific_kundali'),
    path('calc/',     kundali_calculation, name='calc_kundali'),

    # Milan
    path('milan/',    milan_view,    name='milan'),
    path('api/calculate-milan/', calculate_milan_api, name='api_calculate_milan'),
    path('api/save-milan/',      save_milan_api,      name='api_save_milan'),
    path('download-milan-pdf/',  download_milan_pdf,  name='download_milan_pdf'),

    # Admin
    path('admin/',         admin_view,  name='admin_view'),
    path('admin/leads/',   admin_leads, name='admin_leads'),
    path('admin-panel/',   admin_view,  name='admin_view'),
    path('admin-panel/leads/', admin_leads, name='admin_leads'),

    # Payment & Onboarding
    path('submit-payment/', submit_payment,  name='submit_payment'),
    path('onboarding/',     save_onboarding, name='save_onboarding'),

    # Location Save/Clear
    path('api/save-location/', save_default_location,  name='save_default_location'),
    path('api/clear-location/', clear_default_location, name='clear_default_location'),

    # Push Notifications
    path('api/push/vapid-key/',   get_vapid_public_key,     name='vapid_key'),
    path('api/push/subscribe/',   save_push_subscription,   name='push_subscribe'),
    path('api/push/unsubscribe/', delete_push_subscription, name='push_unsubscribe'),
    path('api/push/send/',        admin_send_notification,  name='push_send'),
    path('api/push/test/',        admin_send_notification,  name='push_test'),

    # Rashifal
    path('rashifal/',                  rashifal_home,   name='rashifal'),
    path('rashifal/<str:rashi_id>/',   rashifal_detail, name='rashifal_detail'),
    path('api/rashifal/',              api_rashifal,    name='api_rashifal'),

    # Notifications Mark Read API
    path('api/notifications/mark-read/', mark_notifications_read, name='mark_notifications_read'),

    # Offline
    path('offline/', TemplateView.as_view(template_name='offline.html'), name='offline'),

    # Cron Job / Horoscope Engine
    path('api/bot/send-horoscope/', api_send_daily_horoscope, name='api_send_daily_horoscope'),
    path('hast-rekha/', hast_rekha_view, name='hast_rekha'),
path('api/hast-rekha/analyze/', api_analyze_hast_rekha, name='api_hast_rekha_analyze'),
path('api/hast-rekha/delete/<int:reading_id>/', api_delete_hast_reading, name='api_hast_rekha_delete'),
]
