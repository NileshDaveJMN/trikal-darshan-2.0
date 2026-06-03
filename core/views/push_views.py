# =====================================================
# nayi file banao: core/views/push_views.py
# =====================================================

import json
import os
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from core.models import PushSubscription, UserProfile, SavedKundali
from pywebpush import webpush, WebPushException


def get_vapid_keys():
    return {
        "private": os.environ.get("VAPID_PRIVATE_KEY", ""),
        "public":  os.environ.get("VAPID_PUBLIC_KEY", ""),
        "claims":  {"sub": "mailto:" + os.environ.get("VAPID_EMAIL", "admin@trikaldarshan.com")}
    }


# ─── 1. Public VAPID Key frontend ko do ───
def get_vapid_public_key(request):
    keys = get_vapid_keys()
    return JsonResponse({"publicKey": keys["public"]})


# ─── 2. User ka subscription save karo ───
@require_POST
def save_push_subscription(request):
    try:
        data = json.loads(request.body)
        endpoint = data.get("endpoint")
        p256dh   = data["keys"]["p256dh"]
        auth     = data["keys"]["auth"]

        sub, created = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "user":     request.user,
                "p256dh":   p256dh,
                "auth":     auth,
                "is_active": True,
            }
        )
        return JsonResponse({"status": "ok", "created": created})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


# ─── 3. Subscription delete karo (unsubscribe) ───
@require_POST
def delete_push_subscription(request):
    try:
        data = json.loads(request.body)
        PushSubscription.objects.filter(
            user=request.user,
            endpoint=data.get("endpoint")
        ).delete()
        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


# ─── Helper: Ek user ko notification bhejo ───
def send_push_to_user(user, title, body, url="/"):
    keys = get_vapid_keys()
    if not keys["private"] or not keys["public"]:
        print("[PUSH] VAPID keys missing in environment!")
        return 0

    payload = json.dumps({"title": title, "body": body, "url": url})
    subscriptions = PushSubscription.objects.filter(user=user, is_active=True)
    sent = 0

    for sub in subscriptions:
        try:
            webpush(
                subscription_info=sub.to_dict(),
                data=payload,
                vapid_private_key=keys["private"],
                vapid_claims=keys["claims"],
            )
            sent += 1
        except WebPushException as e:
            print(f"[PUSH] Failed for {sub.endpoint[:40]}... : {e}")
            # 410 Gone = browser ne unsubscribe kar diya
            if "410" in str(e) or "404" in str(e):
                sub.is_active = False
                sub.save()

    return sent


# ─── Helper: Sab users ko notification bhejo ───
def send_push_to_all(title, body, url="/"):
    keys = get_vapid_keys()
    if not keys["private"] or not keys["public"]:
        return {"sent": 0, "failed": 0, "error": "VAPID keys missing"}

    payload = json.dumps({"title": title, "body": body, "url": url})
    subscriptions = PushSubscription.objects.filter(is_active=True)
    sent, failed = 0, 0

    for sub in subscriptions:
        try:
            webpush(
                subscription_info=sub.to_dict(),
                data=payload,
                vapid_private_key=keys["private"],
                vapid_claims=keys["claims"],
            )
            sent += 1
        except WebPushException as e:
            failed += 1
            if "410" in str(e) or "404" in str(e):
                sub.is_active = False
                sub.save()

    return {"sent": sent, "failed": failed}


# ─── 4. Admin: Manual notification bhejo ───
def admin_send_notification(request):
    """Admin panel se manually notification bhejo"""
    if not request.user.is_superuser:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            title  = data.get("title",  "🔮 त्रिकाल दर्शन")
            body   = data.get("body",   "Admin ka sandesh")
            url    = data.get("url",    "/")

            result = send_push_to_all(title, body, url)
            return JsonResponse({
                "status": "ok",
                "sent":   result["sent"],
                "failed": result["failed"],
            })
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    # GET → form dikhao
    total_subs = PushSubscription.objects.filter(is_active=True).count()
    return JsonResponse({"active_subscribers": total_subs})
