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
try:
    from pywebpush import webpush, WebPushException
except ImportError:
    webpush = None
    
    class WebPushException(Exception):
        pass


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
            # 410/404 = browser ne unsubscribe kar diya → delete karo
            if "410" in str(e) or "404" in str(e):
                sub.delete()
                print(f"[PUSH] 🗑️ Expired subscription delete hui: {user.username}")

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
                sub.delete()
                print(f"[PUSH] 🗑️ Expired subscription delete hui (broadcast)")

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


# ================================================================
# FCM (Firebase Cloud Messaging) — Flutter App ke liye
# ================================================================

import json
import os

def _get_fcm_app():
    """Firebase Admin SDK initialize karo (singleton)"""
    try:
        import firebase_admin
        from firebase_admin import credentials
        
        # Already initialized hai to return karo
        try:
            return firebase_admin.get_app()
        except ValueError:
            pass
        
        # Render environment variable se credentials lo
        service_account_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
        if service_account_json:
            cred_dict = json.loads(service_account_json)
            cred = credentials.Certificate(cred_dict)
        else:
            # Local development ke liye file path
            cred = credentials.Certificate("trikal-darshan-firebase-adminsdk.json")
        
        return firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"[FCM] Firebase init error: {e}")
        return None


def send_fcm_to_user(user, title, body, url="/"):
    """Ek user ke sabhi FCM tokens pe notification bhejo"""
    try:
        import firebase_admin
        from firebase_admin import messaging
        from core.models import FCMToken
        
        _get_fcm_app()
        
        tokens = FCMToken.objects.filter(user=user).values_list('token', flat=True)
        if not tokens:
            print(f"[FCM] No FCM tokens for user: {user.username}")
            return 0
        
        sent = 0
        for token in tokens:
            try:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    data={"url": url},  # App mein URL open karne ke liye
                    android=messaging.AndroidConfig(
                        priority="high",
                        notification=messaging.AndroidNotification(
                            icon="ic_notification",
                            color="#FF6B00",  # Trikal Darshan ka orange color
                            sound="default",
                        ),
                    ),
                    token=token,
                )
                firebase_admin.messaging.send(message)
                sent += 1
            except Exception as e:
                print(f"[FCM] Token send failed: {e}")
                # Invalid token → delete karo
                if "registration-token-not-registered" in str(e) or "invalid-registration-token" in str(e):
                    FCMToken.objects.filter(token=token).delete()
                    print(f"[FCM] 🗑️ Invalid token deleted for: {user.username}")
        
        return sent
    except Exception as e:
        print(f"[FCM] send_fcm_to_user error: {e}")
        return 0


def send_fcm_to_all(title, body, url="/"):
    """Sab users ke FCM tokens pe notification bhejo"""
    try:
        import firebase_admin
        from firebase_admin import messaging
        from core.models import FCMToken
        
        _get_fcm_app()
        
        all_tokens = list(FCMToken.objects.values_list('token', flat=True))
        if not all_tokens:
            return {"sent": 0, "failed": 0}
        
        # FCM Multicast — ek baar mein max 500 tokens
        sent, failed = 0, 0
        batch_size = 500
        
        for i in range(0, len(all_tokens), batch_size):
            batch = all_tokens[i:i + batch_size]
            multicast = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                data={"url": url},
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        icon="ic_notification",
                        color="#FF6B00",
                        sound="default",
                    ),
                ),
                tokens=batch,
            )
            response = firebase_admin.messaging.send_each_for_multicast(multicast)
            sent   += response.success_count
            failed += response.failure_count
            
            # Failed tokens clean karo
            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    bad_token = batch[idx]
                    err = str(resp.exception)
                    if "registration-token-not-registered" in err or "invalid-registration-token" in err:
                        FCMToken.objects.filter(token=bad_token).delete()
        
        return {"sent": sent, "failed": failed}
    except Exception as e:
        print(f"[FCM] send_fcm_to_all error: {e}")
        return {"sent": 0, "failed": 0, "error": str(e)}


# ─── FCM Token Save API (Flutter app call karti hai) ───
@csrf_exempt
@require_POST
def save_fcm_token(request):
    """Flutter app se FCM token receive karke save karo"""
    if not request.user.is_authenticated:
        return JsonResponse({"status": "error", "message": "Login required"}, status=401)
    
    try:
        from core.models import FCMToken
        data     = json.loads(request.body)
        token    = data.get("token")
        device_id = data.get("device_id", "default")
        
        if not token:
            return JsonResponse({"status": "error", "message": "Token missing"}, status=400)
        
        FCMToken.objects.update_or_create(
            user=request.user,
            device_id=device_id,
            defaults={"token": token}
        )
        return JsonResponse({"status": "ok", "message": "FCM token saved"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


# ─── FCM Token Delete API (logout pe call karo) ───
@csrf_exempt
@require_POST
def delete_fcm_token(request):
    """Logout pe FCM token delete karo"""
    if not request.user.is_authenticated:
        return JsonResponse({"status": "ok"})
    
    try:
        from core.models import FCMToken
        data     = json.loads(request.body)
        device_id = data.get("device_id", "default")
        FCMToken.objects.filter(user=request.user, device_id=device_id).delete()
        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)
