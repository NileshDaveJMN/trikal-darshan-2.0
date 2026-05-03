from django.db import models
from django.contrib.auth.models import User

# 1. यूजर का प्रोफाइल (Free या Paid स्टेटस के लिए)
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_premium = models.BooleanField(default=False) # Paid service check
    phone_number = models.CharField(max_length=15, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {'Paid' if self.is_premium else 'Free'}"

# 2. सेव की गई कुंडलियों का डेटा (ताकि बार-बार जनरेट न करना पड़े)
class SavedKundali(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='kundalis')
    name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10)
    day = models.IntegerField()
    month = models.IntegerField()
    year = models.IntegerField()
    hour = models.IntegerField()
    minute = models.IntegerField()
    second = models.IntegerField()
    city = models.CharField(max_length=100)
    lat = models.FloatField()
    lon = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

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
    is_chart_paid = models.BooleanField("चार्ट्स टैब (Paid)", default=False)
    is_planets_paid = models.BooleanField("ग्रह स्थिति टैब (Paid)", default=False)
    is_dasha_paid = models.BooleanField("दशा चक्र टैब (Paid)", default=False)
    is_ai_paid = models.BooleanField("AI फलित टैब (Paid)", default=False)

    def __str__(self):
        return "सभी टैब्स की सेटिंग"