from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html

# ✏️ UPDATED: Saare imports top pe consolidate kiye (file ke beech mein
#            duplicate imports the) + EngineRun aur DailyRashifal add kiye
from .models import (UserProfile, SavedKundali, Lead, TabSettings,
                     AIQuestionHistory, KundaliMilanHistory, ManualPayment,
                     AIChatSession, AIChatMessage, UserNotification,
                     LearnCategory, LearnItem,
                     DailyRashifal, EngineRun)

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
    list_display = ('user', 'phone_number', 'is_premium', 'kundali_credits', 'milan_credits', 'profession', 'primary_focus')
    list_editable = ('is_premium', 'kundali_credits', 'milan_credits')
    search_fields = ('user__username', 'user__email', 'phone_number', 'profession', 'primary_focus')
    list_filter = ('is_premium', 'profession', 'relationship_status')

# ==========================================
# 2. MANUAL PAYMENT (AUTO-CREDIT LOGIC)
# ==========================================
@admin.register(ManualPayment)
class ManualPaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'package_type', 'payment_reference', 'amount', 'status', 'date_submitted')
    list_editable = ('status',)
    list_filter = ('status', 'package_type', 'date_submitted')
    search_fields = ('user__username', 'payment_reference')
    readonly_fields = ('date_submitted',)

    def save_model(self, request, obj, form, change):
        if change and obj.status == 'Approved':
            old_obj = ManualPayment.objects.get(pk=obj.pk)
            if old_obj.status != 'Approved':
                profile = obj.user.userprofile
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
                profile.save()
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
# 4.1 AI CHAT (SESSION + MESSAGES)
# ==========================================
class AIChatMessageInline(admin.TabularInline):
    model = AIChatMessage
    extra = 0
    readonly_fields = ('role', 'content', 'created_at')
    can_delete = True
    ordering = ('created_at',)
    fields = ('role', 'content', 'created_at')

    def has_add_permission(self, request, obj=None):
        return False

@admin.register(AIChatSession)
class AIChatSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'get_kundali_name', 'get_user', 'message_count', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('title', 'kundali__name', 'kundali__user__username', 'messages__content')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [AIChatMessageInline]

    def get_kundali_name(self, obj):
        return obj.kundali.name
    get_kundali_name.short_description = "कुंडली"
    get_kundali_name.admin_order_field = 'kundali__name'

    def get_user(self, obj):
        return obj.kundali.user.username if obj.kundali.user else "-"
    get_user.short_description = "User"
    get_user.admin_order_field = 'kundali__user__username'

    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = "कुल Messages"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('kundali', 'kundali__user').prefetch_related('messages')

@admin.register(AIChatMessage)
class AIChatMessageAdmin(admin.ModelAdmin):
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
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('session', 'session__kundali')

# ==========================================
# 4.2 GURUKUL (LEARN)
# ==========================================
class LearnItemInline(admin.TabularInline):
    model = LearnItem
    extra = 1

@admin.register(LearnCategory)
class LearnCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_type', 'order')
    list_filter = ('category_type',)
    search_fields = ('name',)
    inlines = [LearnItemInline]

@admin.register(LearnItem)
class LearnItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_active', 'created_at')
    list_filter = ('category__category_type', 'is_active', 'category')
    search_fields = ('title', 'description')

# ==========================================
# 4.3 USER NOTIFICATIONS
# ==========================================
@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'notification_type', 'is_read', 'created_at')
    list_filter = ('is_read', 'notification_type', 'created_at')
    search_fields = ('title', 'message', 'user__username')
    list_editable = ('is_read',)
    ordering = ('-created_at',)

# ==========================================
# 5. 🆕 ENGINE RUN — Master Engine Reliability Monitor
# ==========================================
@admin.register(EngineRun)
class EngineRunAdmin(admin.ModelAdmin):
    """Roz subah engine ne kya kiya — ek nazar mein:
    SUCCESS (sab theek), PARTIAL (kuch fail), FAILED, INTERRUPTED (beech mein mari)"""
    list_display = ('date', 'status_badge', 'total_users', 'users_ok', 'users_failed',
                    'users_no_kundali', 'notifications_sent', 'duration', 'started_at')
    list_filter = ('status', 'date')
    ordering = ('-started_at',)
    date_hierarchy = 'date'
    # Engine hi likhti hai — admin sirf dekhe
    readonly_fields = [f.name for f in EngineRun._meta.fields]
    search_fields = ('errors',)   # kaunsa user fail hua, directly search karo

    def has_add_permission(self, request):
        return False

    def status_badge(self, obj):
        colors = {'SUCCESS': '#28a745', 'PARTIAL': '#f0ad4e', 'FAILED': '#dc3545',
                  'RUNNING': '#007bff', 'INTERRUPTED': '#6c757d'}
        color = colors.get(obj.status, '#6c757d')
        return format_html('<b style="color:{};">{}</b>', color, obj.get_status_display())
    status_badge.short_description = 'Status'

    def duration(self, obj):
        if obj.started_at and obj.finished_at:
            secs = (obj.finished_at - obj.started_at).total_seconds()
            return f"{int(secs // 60)}m {int(secs % 60)}s"
        return "—"
    duration.short_description = 'समय'

# ==========================================
# 5.1 🆕 DAILY RASHIFAL — General rashifal monitor
# ==========================================
@admin.register(DailyRashifal)
class DailyRashifalAdmin(admin.ModelAdmin):
    """12 rashiyon ka general rashifal — roz ki entries compare karne ke liye
    (upay/nakshatra variation verify karne mein kaam aayega)"""
    list_display = ('date', 'rashi_id', 'general_preview', 'upay_preview')
    list_filter = ('date', 'rashi_id')
    ordering = ('-date', 'rashi_id')
    search_fields = ('general', 'career', 'love', 'health', 'lucky', 'upay')

    def general_preview(self, obj):
        t = obj.general or ''
        return t[:50] + ('...' if len(t) > 50 else '')
    general_preview.short_description = 'सामान्य'

    def upay_preview(self, obj):
        t = obj.upay or ''
        return t[:50] + ('...' if len(t) > 50 else '')
    upay_preview.short_description = 'उपाय'