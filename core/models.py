from django.db import models
from django.contrib.auth.models import User

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
    is_premium = models.BooleanField(default=False)
    
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
    
    # Telegram
    telegram_chat_id = models.CharField(max_length=100, blank=True, null=True)
    daily_horoscope_text = models.TextField(blank=True, null=True)
    horoscope_date = models.DateField(blank=True, null=True)

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
