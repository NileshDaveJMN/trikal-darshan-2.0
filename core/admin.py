from django.contrib import admin
from django.contrib import messages
from .models import (UserProfile, SavedKundali, Lead, TabSettings, 
                     AIQuestionHistory, KundaliMilanHistory, ManualPayment)

# ==========================================
# 🌟 ADMIN DASHBOARD BRANDING 🌟
# ==========================================
admin.site.site_header = "🔮 त्रिकाल दर्शन स्मार्ट एडमिन"
admin.site.site_title = "त्रिकाल दर्शन पोर्टल"
admin.site.index_title = "डैशबोर्ड में आपका स्वागत है"

# ==========================================
# 1. USER PROFILE (CREDIT MANAGEMENT & AI DATA)
# ==========================================
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    # 🌟 बाहर लिस्ट में नए ऑनबोर्डिंग फील्ड्स (Profession, Focus) भी दिखेंगे
    list_display = ('user', 'phone_number', 'is_premium', 'kundali_credits', 'milan_credits', 'profession', 'primary_focus')
    
    # बाहर से ही क्रेडिट्स या प्रीमियम स्टेटस बदलने की सुविधा
    list_editable = ('is_premium', 'kundali_credits', 'milan_credits')
    
    # सर्च में प्रोफेशन और फोकस भी जोड़ दिया
    search_fields = ('user__username', 'user__email', 'phone_number', 'profession', 'primary_focus')
    
    # 🌟 साइडबार में फिल्टर करने की सुविधा (ताकि आप देख सकें कितने यूज़र्स IT में हैं या कितने शादीशुदा हैं)
    list_filter = ('is_premium', 'profession', 'relationship_status')

# ==========================================
# 2. MANUAL PAYMENT (AUTO-CREDIT LOGIC)
# ==========================================
@admin.register(ManualPayment)
class ManualPaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'package_type', 'payment_reference', 'amount', 'status', 'date_submitted')
    # बाहर से ही पेमेंट 'Approved' या 'Pending' करने की सुविधा
    list_editable = ('status',)
    list_filter = ('status', 'package_type', 'date_submitted')
    search_fields = ('user__username', 'payment_reference')
    readonly_fields = ('date_submitted',)

    # 🌟 ऑटो-क्रेडिट का जादुई लॉजिक 🌟
    def save_model(self, request, obj, form, change):
        # चेक करें कि क्या एडमिन ने कोई पुराना रिकॉर्ड बदला है और स्टेटस 'Approved' किया है
        if change and obj.status == 'Approved':
            old_obj = ManualPayment.objects.get(pk=obj.pk)
            
            # सिर्फ तभी क्रेडिट दें जब पुराना स्टेटस 'Approved' ना हो (Double credit से बचने के लिए)
            if old_obj.status != 'Approved':
                profile = obj.user.userprofile
                
                # पैकेज के हिसाब से क्रेडिट्स जोड़ें
                added_k = 0
                added_m = 0
                if obj.package_type == 'KUNDALI_51':
                    profile.kundali_credits += 3
                    added_k = 3
                elif obj.package_type == 'MILAN_51':
                    profile.milan_credits += 3
                    added_m = 3
                elif obj.package_type == 'COMBO_101':
                    profile.kundali_credits += 5
                    profile.milan_credits += 5
                    added_k, added_m = 5, 5
                
                profile.save() # प्रोफाइल में क्रेडिट सेव करें
                
                # एडमिन को सक्सेस मैसेज दिखाएं
                messages.success(request, f"✅ पेमेंट सफल! {obj.user.username} को {added_k} कुंडली और {added_m} मिलान क्रेडिट्स दे दिए गए हैं।")
                
        super().save_model(request, obj, form, change)

# ==========================================
# 3. KUNDALI & MILAN HISTORY
# ==========================================
@admin.register(SavedKundali)
class SavedKundaliAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'city', 'created_at')
    list_filter = ('gender', 'city')
    search_fields = ('name', 'city', 'user__username')

@admin.register(KundaliMilanHistory)
class KundaliMilanHistoryAdmin(admin.ModelAdmin):
    list_display = ('boy_name', 'girl_name', 'total_score', 'is_recommended', 'created_at')
    search_fields = ('boy_name', 'girl_name', 'user__username')
    list_filter = ('is_recommended',)

# ==========================================
# 4. TAB SETTINGS & LEADS
# ==========================================
@admin.register(TabSettings)
class TabSettingsAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_chart_paid', 'is_planets_paid', 'is_dasha_paid', 'is_ai_paid', 'is_dosha_paid', 'is_pdf_paid')
    list_editable = ('is_chart_paid', 'is_planets_paid', 'is_dasha_paid', 'is_ai_paid', 'is_dosha_paid', 'is_pdf_paid')

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'mobile', 'email', 'city', 'created_at')
    list_filter = ('city', 'created_at')
    search_fields = ('name', 'mobile', 'email')

@admin.register(AIQuestionHistory)
class AIQuestionHistoryAdmin(admin.ModelAdmin):
    list_display = ('kundali', 'question', 'created_at')
    search_fields = ('question', 'kundali__name')
