# views/auth_views.py
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from core.models import UserProfile, ManualPayment


def register_view(request):
    if request.method == 'POST':
        u, p, e = request.POST.get('username'), request.POST.get('password'), request.POST.get('email')
        if not User.objects.filter(username=u).exists():
            user = User.objects.create_user(username=u, email=e, password=p)
            UserProfile.objects.get_or_create(user=user)
            login(request, user)
            return redirect('save_onboarding')
            
    return render(request, 'register.html')


def login_view(request):
    if request.method == 'POST':
        u, p = request.POST.get('username'), request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user:
            login(request, user)
            return redirect('/?tab=view-user')
        else:
            messages.error(request, 'यूज़रनेम या पासवर्ड गलत है!')
            
    return render(request, 'login.html')


def user_logout(request):
    logout(request)
    return redirect('/?tab=view-user')


@login_required(login_url='/login/')
def submit_payment(request):
    if request.method == 'POST':
        ref = request.POST.get('reference')
        pkg = request.POST.get('package_type')

        amount = 101 if pkg == 'COMBO_101' else 51

        # Database mein save karo
        ManualPayment.objects.create(
            user=request.user,
            package_type=pkg,
            payment_reference=ref,
            amount=amount,
            status='Pending'
        )

        # User ko success message
        messages.success(request, f"✅ पेमेंट (UTR: {ref}) प्राप्त हुआ! एडमिन अप्रूवल के बाद क्रेडिट्स आपके खाते में जुड़ जाएंगे।")
        return redirect('/?tab=view-user')

    return redirect('home')
