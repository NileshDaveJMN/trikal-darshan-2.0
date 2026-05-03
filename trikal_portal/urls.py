from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    # जांगो का अपना डिफ़ॉल्ट एडमिन पैनल
    path('django-admin/', admin.site.urls), 
    
    # यूजर लॉगिन और रजिस्टर के राउट्स
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('user-logout/', views.user_logout, name='user_logout'),

    # आपके पोर्टल के मेन राउट्स
    path('', views.index, name='home'),
    path('api/get_ai_analysis/', views.api_get_ai_analysis, name='api_get_ai_analysis'),
    path('panchang/', views.panchang, name='panchang'),
    path('contact/', views.contact, name='contact'),
    
    # आपका कस्टम एडमिन और ट्रैकिंग
    path('admin/', views.admin_view, name='admin_view'),
    path('admin/leads', views.admin_leads, name='admin_leads'),
    path('logout/', views.logout_view, name='logout'),
] # 👈 ध्यान दें: ब्रैकेट यहाँ पूरी तरह बंद हो गया है!

# 🌟 कस्टम ब्रांडिंग वाले कोड (ब्रैकेट के एकदम बाहर और नीचे):
admin.site.site_header = "त्रिकाल दर्शन एडमिन"
admin.site.site_title = "त्रिकाल पोर्टल"
admin.site.index_title = "कंट्रोल पैनल में आपका स्वागत है"
