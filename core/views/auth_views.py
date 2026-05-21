# views/auth_views.py
from django.contrib import messages # 🌟 इसे सबसे ऊपर इम्पोर्ट करें
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from core.models import UserProfile 
from core.models import ManualPayment
from django.contrib.auth.decorators import login_required
import urllib.request
import urllib.parse

def register_view(request):
    if request.method == 'POST':
        u, p, e = request.POST.get('username'), request.POST.get('password'), request.POST.get('email')
        if not User.objects.filter(username=u).exists():
            user = User.objects.create_user(username=u, email=e, password=p)
            UserProfile.objects.create(user=user)
            return redirect('login')
    return render(request, 'register.html')

def login_view(request):
    if request.method == 'POST':
        u, p = request.POST.get('username'), request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user:
            login(request, user)
            return redirect('/?tab=view-user')
        else:
            # 🌟 यह लाइन बताएगी कि लॉगिन क्यों नहीं हुआ
            messages.error(request, 'यूज़रनेम या पासवर्ड गलत है!') 
            
    return render(request, 'login.html')

def user_logout(request):
    logout(request)
    return redirect('/?tab=view-user')
from django.shortcuts import redirect
from django.contrib import messages
from core.models import ManualPayment
from django.contrib.auth.decorators import login_required

@login_required(login_url='/login/')
def submit_payment(request):
    if request.method == 'POST':
        ref = request.POST.get('reference')
        pkg = request.POST.get('package_type')
        
        # अमाउंट तय करना
        amount = 101 if pkg == 'COMBO_101' else 51
        
        # 1. डेटाबेस (एडमिन) में सेव करना
        ManualPayment.objects.create(
            user=request.user,
            package_type=pkg,
            payment_reference=ref,
            amount=amount,
            status='Pending'
        )
        
        # 2. 🌟 बैकएंड से टेलीग्राम पर सुरक्षित अलर्ट भेजना 🌟
        try:
            bot_token = "8353256217:AAG58hIdMPaUypfU4fXVlU3lJGJZhZ2QN1I"
            chat_id = "8943971061"
            
            # पैकेज का साफ नाम दिखाने के लिए
            pkg_name = "कॉम्बो पैक (₹101)" if pkg == 'COMBO_101' else ("कुंडली पैक (₹51)" if pkg == 'KUNDALI_51' else "मिलान पैक (₹51)")
            
            message_text = f"🔔 *नया रिचार्ज अलर्ट* 🔔\n\n👤 *यूज़र:* {request.user.username}\n📦 *पैकेज:* {pkg_name}\n📱 *UTR:* {ref}\n⏳ *स्थिति:* Pending\n\n👉 कृपया एडमिन पैनल में जाकर अप्रूव करें।"
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = urllib.parse.urlencode({'chat_id': chat_id, 'text': message_text, 'parse_mode': 'Markdown'}).encode('utf-8')
            
            # टेलीग्राम को रिक्वेस्ट भेजना
            urllib.request.urlopen(url, data=data, timeout=5)
        except Exception as e:
            print("Telegram Error:", e) # अगर नेट बंद हो तो साइट क्रैश नहीं होगी
        
        # 3. यूज़र को सक्सेस मैसेज दिखाना
        messages.success(request, f"✅ पेमेंट (UTR: {ref}) प्राप्त हुआ! एडमिन अप्रूवल के बाद क्रेडिट्स आपके खाते में जुड़ जाएंगे।")
        return redirect('/?tab=view-user')  # वापस प्रोफाइल टैब पर भेजें
    
    return redirect('home')