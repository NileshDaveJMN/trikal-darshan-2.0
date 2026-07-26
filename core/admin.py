from django.contrib import admin
from django.contrib import messages
from .models import (UserProfile, SavedKundali, Lead, TabSettings, 
                     AIQuestionHistory, KundaliMilanHistory, ManualPayment,
                     AIChatSession, AIChatMessage)

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

# ==========================================
# 4.1 AI CHAT (SESSION + MESSAGES) — नया Chat feature
# ==========================================

# 🌟 Session ke andar hi saare messages inline (WhatsApp jaisa chat log) दिखेंगे
class AIChatMessageInline(admin.TabularInline):
    model = AIChatMessage
    extra = 0
    # ✅ AI/user ke asli messages edit na ho sakein (सिर्फ audit/view के लिए)
    readonly_fields = ('role', 'content', 'created_at')
    can_delete = True          # spam/abuse wala single message delete karne ki suvidha
    ordering = ('created_at',)
    fields = ('role', 'content', 'created_at')

    def has_add_permission(self, request, obj=None):
        # Admin naye AI/user messages manually inject na kar sake
        return False


@admin.register(AIChatSession)
class AIChatSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'get_kundali_name', 'get_user', 'message_count', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('title', 'kundali__name', 'kundali__user__username', 'messages__content')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [AIChatMessageInline]

    # किस kundali ki chat hai
    def get_kundali_name(self, obj):
        return obj.kundali.name
    get_kundali_name.short_description = "कुंडली"
    get_kundali_name.admin_order_field = 'kundali__name'

    # किस user ki chat hai (kundali se user tak pahunchna)
    def get_user(self, obj):
        return obj.kundali.user.username if obj.kundali.user else "-"
    get_user.short_description = "User"
    get_user.admin_order_field = 'kundali__user__username'

    # is session me kitne messages hain (quick glance ke liye)
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = "कुल Messages"

    # N+1 query se bachne ke liye
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('kundali', 'kundali__user').prefetch_related('messages')


@admin.register(AIChatMessage)
class AIChatMessageAdmin(admin.ModelAdmin):
    # 🌟 Alag se bhi register kiya — taaki admin saare users ke saare
    # AI messages me ek saath (bina session open kiye) search/filter kar sake,
    # jaise koi abusive/spam content dhoondhna ho toh
    list_display = ('get_kundali_name', 'session', 'role', 'short_content', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('content', 'session__title', 'session__kundali__name')
    readonly_fields = ('session', 'role', 'content', 'created_at')

    def get_kundali_name(self, obj):
        return obj.session.kundali.name
    get_kundali_name.short_description = "कुंडली"
    get_kundali_name.admin_order_field = 'session__kundali__name'

    def short_content(self, obj):
        return obj.content[:60] + ("..." if len(obj.content) > 60 else "")
    short_content.short_description = "Message"

    def has_add_permission(self, request):
        # Manually naya message create karne ka koi use-case nahi
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('session', 'session__kundali')

from django.contrib import admin
from .models import LearnCategory, LearnItem

# यह क्लास एडमिन पैनल में कैटेगरी के अंदर ही वीडियो/PDF जोड़ने का ऑप्शन देगी
class LearnItemInline(admin.TabularInline):
    model = LearnItem
    extra = 1

@admin.register(LearnCategory)
class LearnCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_type', 'order')
    list_filter = ('category_type',)
    search_fields = ('name',)
    inlines = [LearnItemInline] # इससे फोल्डर के अंदर ही आइटम दिखेंगे

@admin.register(LearnItem)
class LearnItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_active', 'created_at')
    list_filter = ('category__category_type', 'is_active', 'category')
    search_fields = ('title', 'description')

# =====================================================
# core/admin.py
# =====================================================
from django.contrib import admin
from .models import UserNotification

@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    # एडमिन की लिस्ट में कौन-कौन से कॉलम दिखेंगे
    list_display = ('title', 'user', 'notification_type', 'is_read', 'created_at')
    
    # दाईं तरफ फिल्टर लगाने का ऑप्शन (नया/पुराना, यूज़र वाइज, टाइप वाइज)
    list_filter = ('is_read', 'notification_type', 'created_at')
    
    # सर्च करने के लिए फील्ड्स
    search_fields = ('title', 'message', 'user__username')
    
    # लिस्ट में ही 'is_read' को एडिट करने का मौका दें (Quick check)
    list_editable = ('is_read',)
    
    # डिफ़ॉल्ट सॉर्टिंग (नया सबसे ऊपर)
    ordering = ('-created_at',)

    # एडमिन में दिखने वाला नाम (Optional, model Meta में भी कर सकते हैं)
    # def get_queryset(self, request):
    #     queryset = super().get_queryset(request)
    #     return queryset

