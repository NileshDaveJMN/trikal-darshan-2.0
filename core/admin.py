from django.contrib import admin
from .models import UserProfile, SavedKundali, Lead
from .models import TabSettings

@admin.register(TabSettings)
class TabSettingsAdmin(admin.ModelAdmin):
    # यह कोड लिस्ट में ही चारों टिक-बॉक्स दिखा देगा!
    list_display = ('__str__', 'is_chart_paid', 'is_planets_paid', 'is_dasha_paid', 'is_ai_paid')
    list_editable = ('is_chart_paid', 'is_planets_paid', 'is_dasha_paid', 'is_ai_paid')
    
@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    # अब एडमिन लिस्ट में नाम, मोबाइल, ईमेल और शहर दिखेगा
    list_display = ('name', 'mobile', 'email', 'city', 'created_at')
    list_filter = ('city',)
    search_fields = ('name', 'mobile', 'email')


admin.site.register(UserProfile)
admin.site.register(SavedKundali)

