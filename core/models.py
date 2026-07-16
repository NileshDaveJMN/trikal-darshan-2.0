from django.db import models
from django.contrib.auth.models import User
import datetime

class SavedKundali(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, default="पुरुष")
    day = models.IntegerField()
    month = models.IntegerField()
    year = models.IntegerField()
    hour = models.IntegerField()
    minute = models.IntegerField()
    second = models.IntegerField(default=0)
    city = models.CharField(max_length=100)
    lat = models.FloatField()
    lon = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.day}/{self.month}/{self.year})"

class AIQuestionHistory(models.Model):
    kundali = models.ForeignKey(SavedKundali, on_delete=models.CASCADE, related_name='ai_histories')
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AI: {self.kundali.name} - {self.question[:30]}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True)
    is_premium = models.BooleanField(default=False) # VIP Subscription ke liye
    
    # Credit System
    kundali_credits = models.IntegerField("Kundali Credits", default=1)
    milan_credits = models.IntegerField("Milan Credits", default=1)
    
    # Onboarding fields
    primary_focus = models.CharField(max_length=100, blank=True, null=True)
    current_challenge = models.CharField(max_length=100, blank=True, null=True)
    relationship_status = models.CharField(max_length=100, blank=True, null=True)
    profession = models.CharField(max_length=100, blank=True, null=True)
    finance_focus = models.CharField(max_length=100, blank=True, null=True)
    activity_level = models.CharField(max_length=100, blank=True, null=True)
    travel_habit = models.CharField(max_length=100, blank=True, null=True)
    
    # 🌟 Default Location (Panchang ke liye)
    default_city = models.CharField(max_length=100, blank=True, null=True)
    default_lat  = models.FloatField(blank=True, null=True)
    default_lon  = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} (K: {self.kundali_credits}, M: {self.milan_credits})"

class ManualPayment(models.Model):
    PACKAGE_CHOICES = [
        ('KUNDALI_51', 'Kundali Pack (3 Credits) - ₹51'),
        ('MILAN_51', 'Milan Pack (3 Credits) - ₹51'),
        ('COMBO_101', 'Combo Pack (5+5 Credits) - ₹101'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    package_type = models.CharField(max_length=20, choices=PACKAGE_CHOICES, default='KUNDALI_51')
    payment_reference = models.CharField(max_length=50, help_text="UPI Mobile Number OR 12-digit UTR")
    amount = models.IntegerField(default=51)
    status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Approved', 'Approved')],
        default='Pending'
    )
    date_submitted = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.package_type} - {self.status}"

class Lead(models.Model):
    name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15, default="", blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    city = models.CharField(max_length=100, default="वेबसाइट", blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class TabSettings(models.Model):
    is_chart_paid   = models.BooleanField("चार्ट्स टैब (Paid)", default=False)
    is_planets_paid = models.BooleanField("ग्रह स्थिति टैब (Paid)", default=False)
    is_dasha_paid   = models.BooleanField("दशा चक्र टैब (Paid)", default=False)
    is_ai_paid      = models.BooleanField("AI फलित टैब (Paid)", default=False)
    is_dosha_paid   = models.BooleanField("दोष एवं उपाय टैब (Paid)", default=False)
    is_pdf_paid     = models.BooleanField("PDF डाउनलोड (Paid)", default=False)

    def __str__(self):
        return "सभी टैब्स की सेटिंग"

class DailyRashifal(models.Model):
    date = models.DateField(default=datetime.date.today)
    rashi_id = models.CharField(max_length=20)
    
    general = models.TextField(blank=True, null=True)
    career = models.TextField(blank=True, null=True)
    love = models.TextField(blank=True, null=True)
    health = models.TextField(blank=True, null=True)
    lucky = models.TextField(blank=True, null=True)
    upay = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('date', 'rashi_id')
        
    def __str__(self):
        return f"{self.rashi_id} - {self.date}"

class KundaliMilanHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    boy_name = models.CharField(max_length=100)
    girl_name = models.CharField(max_length=100)
    total_score = models.FloatField()
    manglik_status = models.CharField(max_length=200, blank=True, null=True)
    is_recommended = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    boy_nakshatra = models.CharField(max_length=50, blank=True, null=True)
    boy_rashi = models.CharField(max_length=50, blank=True, null=True)
    girl_nakshatra = models.CharField(max_length=50, blank=True, null=True)
    girl_rashi = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.boy_name} & {self.girl_name} - Score: {self.total_score}/36"

# Auto-create UserProfile
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    UserProfile.objects.get_or_create(user=instance)

class PushSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.TextField(unique=True)
    p256dh = models.TextField()
    auth = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - Push Sub"

    def to_dict(self):
        return {
            "endpoint": self.endpoint,
            "keys": {
                "p256dh": self.p256dh,
                "auth": self.auth,
            }
        }

# 1. प्लेलिस्ट या लाइब्रेरी टॉपिक बनाने के लिए (Category)
class LearnCategory(models.Model):
    CATEGORY_TYPES = (
        ('PLAYLIST', '🎥 वीडियो प्लेलिस्ट'),
        ('LIBRARY', '📚 ई-लाइब्रेरी (PDF टॉपिक)'),
    )
    name = models.CharField(max_length=100, verbose_name="कैटेगरी का नाम (जैसे: बेसिक ज्योतिष)")
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPES, verbose_name="प्रकार")
    order = models.IntegerField(default=0, verbose_name="क्रम (Order) - ऊपर दिखाने के लिए 1 लिखें")

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f"[{self.get_category_type_display()}] {self.name}"

# 2. उस प्लेलिस्ट/टॉपिक के अंदर वीडियो या PDF डालने के लिए (Item)
class LearnItem(models.Model):
    category = models.ForeignKey(LearnCategory, on_delete=models.CASCADE, related_name='items', verbose_name="किस प्लेलिस्ट/लाइब्रेरी में डालें?")
    title = models.CharField(max_length=200, verbose_name="टाइटल")
    description = models.TextField(verbose_name="विवरण")
    cover_emoji = models.CharField(max_length=10, default="📕", verbose_name="आइकॉन (Emoji)")
    
    pdf_file = models.URLField(blank=True, null=True, verbose_name="PDF Google Drive Link")
    video_url = models.URLField(blank=True, null=True, verbose_name="वीडियो लिंक")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return self.title

class UserNotification(models.Model):
    NOTIFICATION_TYPES = (
        ('DAILY', 'दैनिक राशिफल'),
        ('GOCHAR', 'गोचर परिवर्तन'),
        ('DASHA', 'दशा परिवर्तन'),
        ('FESTIVAL', 'त्यौहार / विशेष उपाय'),
        ('SYSTEM', 'सिस्टम अलर्ट'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200, verbose_name="शीर्षक (Title)")
    message = models.TextField(verbose_name="संदेश (Message)")
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='DAILY')
    is_read = models.BooleanField(default=False, verbose_name="क्या पढ़ लिया गया?")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at'] # इससे सबसे नए नोटिफिकेशन हमेशा ऊपर दिखेंगे

    def __str__(self):
        return f"[{self.get_notification_type_display()}] {self.user.username} - {self.title}"

class HastRekhaReading(models.Model):
    HAND_CHOICES = [
        ('दाहिना हाथ', 'दाहिना हाथ (Right Hand)'),
        ('बायाँ हाथ',  'बायाँ हाथ (Left Hand)'),
    ]
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hast_readings')
    hand_type  = models.CharField(max_length=20, choices=HAND_CHOICES, default='दाहिना हाथ')
    prediction = models.TextField(verbose_name="हस्त रेखा विश्लेषण")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.hand_type} ({self.created_at.strftime('%d/%m/%Y')})"

class FCMToken(models.Model):
    """Flutter App ke liye Firebase Cloud Messaging Token"""
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fcm_tokens')
    token      = models.TextField(verbose_name="FCM Device Token")
    device_id  = models.CharField(max_length=200, blank=True, null=True, verbose_name="Device ID (optional)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        # Ek device pe ek hi token hoga
        unique_together = ('user', 'device_id')

    def __str__(self):
        return f"{self.user.username} - FCM ({self.updated_at.strftime('%d/%m/%Y')})"

# ============================================================
# models.py mein ye do classes ADD karo (existing ke neeche)
# ============================================================

class AIChatSession(models.Model):
    """Ek kundali ki ek chat session — user kai sessions rakh sakta hai"""
    kundali    = models.ForeignKey(SavedKundali, on_delete=models.CASCADE, related_name='chat_sessions')
    title      = models.CharField(max_length=200, default="नई बातचीत", verbose_name="Chat का शीर्षक")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.kundali.name} - {self.title} ({self.created_at.strftime('%d/%m/%Y')})"


class AIChatMessage(models.Model):
    """Ek session ke andar har ek message — user ya assistant"""
    ROLE_CHOICES = [
        ('user',      'User'),
        ('assistant', 'Assistant'),
    ]
    session    = models.ForeignKey(AIChatSession, on_delete=models.CASCADE, related_name='messages')
    role       = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content    = models.TextField(verbose_name="Message Content")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']   # purane messages pehle

    def __str__(self):
        return f"[{self.role}] {self.session.kundali.name}: {self.content[:40]}"
